using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Drawing;
using System.Diagnostics;
using System.Globalization;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;
class Wizard:Form{
 bool ru=CultureInfo.CurrentUICulture.TwoLetterISOLanguageName=="ru",busy=false;
 TextBox donor=new TextBox(),doors=new TextBox(),containers=new TextBox(),output=new TextBox(),log=new TextBox();
 Button create=new Button(),open=new Button(),autodetect=new Button();Label result=new Label();ProgressBar progress=new ProgressBar();
 List<Control> inputs=new List<Control>();string archive="";string home=AppDomain.CurrentDomain.BaseDirectory;
 string T(string en,string russian){return ru?russian:en;}
 public Wizard(){
  Text="SVR Visual Compatibility Generator 0.4 Beta";ClientSize=new Size(850,656);MinimumSize=new Size(790,640);StartPosition=FormStartPosition.CenterScreen;Font=new Font("Segoe UI",10);BackColor=Color.FromArgb(245,246,248);AutoScaleMode=AutoScaleMode.Dpi;
  var title=new Label{Text=T("Match your physical doors and containers to your graphics mods","Внешний вид дверей и контейнеров под вашу сборку"),Location=new Point(24,20),Size=new Size(800,30),Font=new Font("Segoe UI",14,FontStyle.Bold)};Controls.Add(title);
  Controls.Add(new Label{Text=T("Choose folders, then create an installable MO2 patch. Python is included.","Выберите папки и создайте готовый патч для MO2. Python уже включён."),Location=new Point(24,54),Size=new Size(800,24)});
  autodetect.Text=T("Find SVR mods in MO2…","Найти SVR-моды в MO2…");autodetect.SetBounds(24,89,260,32);Controls.Add(autodetect);autodetect.Click+=(s,e)=>FindMods();inputs.Add(autodetect);
  var help=new Label{Text=T("Use one or both mods. Leave uninstalled mods blank.","Один или оба мода. Пустое поле — мод не установлен."),Location=new Point(300,92),Size=new Size(520,36)};Controls.Add(help);
  Row(T("SVR Physical Doors folder (optional)","Папка SVR Physical Doors (необязательно)"),doors,138);
  Row(T("SVR Physical Containers folder (optional)","Папка SVR Physical Containers (необязательно)"),containers,210);
  Row(T("Graphics / PGPatcher output folder or its meshes folder","Папка графики / результата PGPatcher или её папка meshes"),donor,282);
  Row(T("Save the generated ZIP here","Куда сохранить готовый ZIP"),output,354);
  output.Text=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"SVR Visual Patches");
  create.Text=T("Create patch","Создать патч");create.SetBounds(24,435,230,40);Controls.Add(create);create.Click+=async(s,e)=>await Build();
  open.Text=T("Open result folder","Открыть папку результата");open.SetBounds(270,435,245,40);open.Enabled=false;Controls.Add(open);open.Click+=(s,e)=>{if(File.Exists(archive))Process.Start("explorer.exe","/select,"+Quote(archive));};
  progress.SetBounds(535,448,285,14);Controls.Add(progress);
  result.SetBounds(24,489,800,42);Controls.Add(result);
  log.SetBounds(24,539,800,91);log.Anchor=AnchorStyles.Top|AnchorStyles.Bottom|AnchorStyles.Left|AnchorStyles.Right;log.Multiline=true;log.ReadOnly=true;log.ScrollBars=ScrollBars.Vertical;log.BackColor=Color.White;Controls.Add(log);
  result.Text=T("Your installed mods and MO2 profiles are never modified.","Установленные моды и профили MO2 не изменяются.");
  FormClosing+=(s,e)=>{if(busy){e.Cancel=true;MessageBox.Show(T("Please wait until generation finishes.","Дождитесь завершения генерации."));}};
 }
 void Row(string label,TextBox box,int y){
  Controls.Add(new Label{Text=label,Location=new Point(24,y),Size=new Size(800,23)});box.SetBounds(24,y+25,676,29);box.Anchor=AnchorStyles.Left|AnchorStyles.Top|AnchorStyles.Right;Controls.Add(box);inputs.Add(box);
  var button=new Button{Text=T("Browse…","Выбрать…"),Location=new Point(712,y+24),Size=new Size(112,31),Anchor=AnchorStyles.Top|AnchorStyles.Right};Controls.Add(button);inputs.Add(button);
  button.Click+=(s,e)=>{using(var dialog=new FolderBrowserDialog()){dialog.Description=label;dialog.ShowNewFolderButton=true;if(Directory.Exists(box.Text))dialog.SelectedPath=box.Text;if(dialog.ShowDialog()==DialogResult.OK)box.Text=dialog.SelectedPath;}};
 }
 public static string Quote(string value){var b=new StringBuilder("\"");int slashes=0;foreach(char c in value){if(c=='\\'){slashes++;continue;}if(c=='\"'){b.Append('\\',slashes*2+1);b.Append(c);slashes=0;continue;}b.Append('\\',slashes);slashes=0;b.Append(c);}b.Append('\\',slashes*2);b.Append('"');return b.ToString();}
 static string[] Mods(string path,string dll){return Directory.GetDirectories(path).Where(d=>File.Exists(Path.Combine(d,"SKSE","Plugins",dll))).ToArray();}
 void FindMods(){using(var dialog=new FolderBrowserDialog()){
  dialog.Description=T("Select MO2's mods folder","Выберите папку mods вашего MO2");
  foreach(var drive in DriveInfo.GetDrives().Where(d=>d.IsReady)){var p=Path.Combine(drive.RootDirectory.FullName,"MO2","mods");if(Directory.Exists(p)){dialog.SelectedPath=p;break;}}
  if(dialog.ShowDialog()!=DialogResult.OK)return;
  try{
   string mods=dialog.SelectedPath;if(Directory.Exists(Path.Combine(mods,"mods")))mods=Path.Combine(mods,"mods");
   var a=Mods(mods,"SVRPhysicalDoors.dll");var b=Mods(mods,"SVRPhysicalContainers.dll");doors.Text=a.Length==1?a[0]:"";containers.Text=b.Length==1?b[0]:"";
   log.Text=T("Doors found: ","Найдено модов дверей: ")+a.Length+"; "+T("containers found: ","контейнеров: ")+b.Length+Environment.NewLine;
   if(a.Length>1 || b.Length>1)log.AppendText(T("Multiple copies found. Choose the active base mod folders manually.","Найдено несколько копий. Выберите активные папки базовых модов вручную.")+Environment.NewLine);
   var guess=Directory.GetDirectories(mods).Where(d=>d.IndexOf("output",StringComparison.OrdinalIgnoreCase)>=0 && Directory.Exists(Path.Combine(d,"meshes"))).ToArray();
   if(guess.Length==1){donor.Text=guess[0];log.AppendText(T("Graphics output suggested. Verify that it is the current PGPatcher result.","Предложена папка графики. Проверьте, что это актуальный результат PGPatcher."));}
   if(a.Length+b.Length==0)MessageBox.Show(T("No SVR base DLLs found. Select the correct MO2 mods folder.","Базовые DLL SVR не найдены. Выберите правильную папку mods."));
  }catch(Exception ex){MessageBox.Show(ex.Message);}
 }}
 async Task Build(){
  if(busy)return;
  if(string.IsNullOrWhiteSpace(doors.Text) && string.IsNullOrWhiteSpace(containers.Text)){MessageBox.Show(T("Choose at least one SVR mod folder.","Выберите папку хотя бы одного SVR-мода."));return;}
  if(!Directory.Exists(donor.Text)){MessageBox.Show(T("Choose the graphics/PGPatcher output folder.","Выберите папку графики или результата PGPatcher."));return;}
  string dest;
  try{dest=Path.Combine(Path.GetFullPath(output.Text),"SVR Visual Patch "+DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss")+"_"+Guid.NewGuid().ToString("N").Substring(0,4));}
  catch(Exception ex){MessageBox.Show(ex.Message);return;}
  busy=true;create.Enabled=false;open.Enabled=false;foreach(var c in inputs)c.Enabled=false;progress.Style=ProgressBarStyle.Marquee;log.Clear();result.Text=T("Generating and checking models…","Генерация и проверка моделей…");
  try{
   var args=Quote(Path.Combine(home,"app","gui_worker.py"))+" --donor "+Quote(donor.Text)+" --output "+Quote(dest);
   if(!string.IsNullOrWhiteSpace(doors.Text))args+=" --doors "+Quote(doors.Text);if(!string.IsNullOrWhiteSpace(containers.Text))args+=" --containers "+Quote(containers.Text);
   var start=new ProcessStartInfo(Path.Combine(home,"runtime","python.exe"),args){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true,WorkingDirectory=home};
   var info=await Task.Run(async()=>{using(var p=Process.Start(start)){var stdout=p.StandardOutput.ReadToEndAsync();var stderr=p.StandardError.ReadToEndAsync();await Task.Run(()=>p.WaitForExit());return new Tuple<int,string,string>(p.ExitCode,await stdout,await stderr);}});
   Directory.CreateDirectory(Path.GetDirectoryName(dest));File.WriteAllText(dest+".log",info.Item2+Environment.NewLine+info.Item3,Encoding.UTF8);
   log.Text=info.Item2+Environment.NewLine+info.Item3;
   if(info.Item1!=0){result.Text=T("Patch not created. See the log below. Inputs were not changed.","Патч не создан. Ошибка указана в журнале ниже. Исходные моды не изменены.");log.Text=info.Item3.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries).FirstOrDefault()+Environment.NewLine+T("Full log saved: ","Подробный журнал сохранён: ")+dest+".log";return;}
   var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(Path.Combine(dest,"summary.json")));archive=(string)data["archive"];
   int skipped=Convert.ToInt32(data["unsupported"])+Convert.ToInt32(data["missing_donor"]);
   result.Text=T("Ready: ","Готово: ")+data["patched"]+T(" models patched. Skipped/unsupported: "," моделей. Пропущено / не поддерживается: ")+skipped+".";
   log.Clear();
   if(skipped>0)log.AppendText(T("Some models were left unchanged. Details: ","Часть моделей оставлена без изменений. Подробности: ")+(string)data["report"]+Environment.NewLine);
   log.AppendText(Environment.NewLine+T("Install this ZIP in MO2 after the SVR mods and graphics output:","Установите этот ZIP в MO2 ниже SVR-модов и результата обработки графики:")+Environment.NewLine+archive);
   open.Enabled=true;
  }catch(Exception ex){result.Text=T("Generation failed; no input mods were changed.","Не удалось создать патч. Исходные моды не изменены.");log.Text=ex.ToString();}
  finally{busy=false;create.Enabled=true;foreach(var c in inputs)c.Enabled=true;progress.Style=ProgressBarStyle.Blocks;}
 }
 [STAThread] static int Main(string[] args){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
  if(args.Length==2 && (args[0]=="--render-test" || args[0]=="--render-test-en")){if(args[0]=="--render-test-en")System.Threading.Thread.CurrentThread.CurrentUICulture=new CultureInfo("en-US");using(var form=new Wizard()){form.StartPosition=FormStartPosition.Manual;form.Location=new Point(-32000,-32000);form.ShowInTaskbar=false;form.Show();Application.DoEvents();form.PerformLayout();using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(args[1]);}}return 0;}
  if(args.Length==2 && args[0]=="--selftest"){
   var data=new JavaScriptSerializer().Deserialize<Dictionary<string,string>>(File.ReadAllText(args[1]));
   var testForm=new Wizard();testForm.ShowInTaskbar=false;testForm.Opacity=0;testForm.StartPosition=FormStartPosition.Manual;testForm.Location=new Point(-32000,-32000);
   testForm.Shown+=async(s,e)=>{testForm.donor.Text=data["donor"];testForm.doors.Text=data.ContainsKey("doors")?data["doors"]:"";testForm.containers.Text=data.ContainsKey("containers")?data["containers"]:"";testForm.output.Text=data["output"];await testForm.Build();File.WriteAllText(data["result"],new JavaScriptSerializer().Serialize(new{archive=testForm.archive,exists=File.Exists(testForm.archive),buttonEnabled=testForm.open.Enabled,status=testForm.result.Text,log=testForm.log.Text}));testForm.Close();};
   Application.Run(testForm);return 0;
  }
  Application.Run(new Wizard());return 0;
 }
}
