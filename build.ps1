param(
 [Parameter(Mandatory=$true)][string]$PythonZip,
 [string]$CMakeExe='cmake',
 [string]$Generator=''
)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskBuild=Join-Path $taskRoot 'build'
$taskPackage=Join-Path $taskBuild 'SVR Visual Compatibility Generator'
if(Test-Path -LiteralPath $taskPackage){throw 'Build package already exists. Move it elsewhere before rebuilding.'}
$taskPythonZip=(Resolve-Path -LiteralPath $PythonZip).Path
$taskExpected='90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159'
if((Get-FileHash -LiteralPath $taskPythonZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpected){throw 'Python ZIP SHA256 does not match the reviewed official 3.14.10 x64 embeddable package.'}
$taskCmakeArgs=@('-S',(Join-Path $taskRoot 'native'),'-B',(Join-Path $taskBuild 'native'))
if($Generator -notmatch 'Ninja'){$taskCmakeArgs+=@('-A','x64')}
if($Generator){$taskCmakeArgs+=@('-G',$Generator)}
if($Generator -eq 'Ninja'){$taskCmakeArgs+=@('-DCMAKE_BUILD_TYPE=Release','-DCMAKE_TRY_COMPILE_CONFIGURATION=Release','-DCMAKE_CXX_FLAGS_DEBUG=/Od')}
& $CMakeExe @taskCmakeArgs
if($LASTEXITCODE -ne 0){throw 'CMake configure failed'}
& $CMakeExe --build (Join-Path $taskBuild 'native') --config Release --parallel 2
if($LASTEXITCODE -ne 0){throw 'Native build failed'}
New-Item -ItemType Directory -Path (Join-Path $taskPackage 'app') -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'app') -File | Copy-Item -Destination (Join-Path $taskPackage 'app')
$taskNativeExe=Join-Path $taskBuild 'native/Release/SVRVisualPatch.exe'
if($Generator -match 'Ninja'){$taskNativeExe=Join-Path $taskBuild 'native/SVRVisualPatch.exe'}
Copy-Item -LiteralPath $taskNativeExe -Destination (Join-Path $taskPackage 'app/SVRVisualPatch.exe')
$taskCsc=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$taskCscArgs=@('/nologo','/target:winexe','/platform:x64','/optimize+','/utf8output','/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.Web.Extensions.dll',('/out:'+(Join-Path $taskPackage 'SVR Visual Compatibility.exe')),(Join-Path $taskRoot 'gui/Wizard.cs'))
& $taskCsc @taskCscArgs
if($LASTEXITCODE -ne 0){throw 'GUI build failed'}
Expand-Archive -LiteralPath $taskPythonZip -DestinationPath (Join-Path $taskPackage 'runtime')
Set-Content -LiteralPath (Join-Path $taskPackage 'runtime/python314._pth') -Value "python314.zip`n.`n../app`n" -Encoding ascii
foreach($taskFile in @('COPYING.txt','nifly-LICENSE.txt','README.md')){Copy-Item -LiteralPath (Join-Path $taskRoot $taskFile) -Destination $taskPackage}
Write-Output "Build complete: $taskPackage"
Write-Output 'Rebuilding is supported; bit-for-bit executable reproducibility is not claimed across compiler versions.'
