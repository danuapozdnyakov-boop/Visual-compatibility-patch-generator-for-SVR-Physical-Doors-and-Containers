#include "NifFile.hpp"
#include <fstream>
#include <sstream>
#include <iostream>
#include <map>
using namespace nifly;
std::filesystem::path longPath(const wchar_t* input){
 auto value=std::filesystem::absolute(std::filesystem::path(input)).lexically_normal().wstring();
 if(value.rfind(L"\\\\?\\",0)==0)return value;
 if(value.rfind(L"\\\\",0)==0)return std::wstring(L"\\\\?\\UNC\\")+value.substr(2);
 return std::wstring(L"\\\\?\\")+value;
}
MatTransform global(NifFile& n,NiAVObject* obj){auto t=obj->transform;auto p=n.GetParentNode(obj);unsigned count=0;while(p && count++<128){t=p->transform.ComposeTransforms(t);p=n.GetParentNode(p);}if(count>=128)throw std::runtime_error("cyclic hierarchy");return t;}
void unlinkShape(NifFile& n,NiObject* shape){
 const auto id=n.GetBlockID(shape);
 for(auto node:n.GetNodes())for(uint32_t i=node->childRefs.GetSize();i>0;--i)if(node->childRefs.GetBlockRef(i-1)==id)node->childRefs.RemoveBlockRef(i-1);
}
int convertLegacyDonor(const wchar_t* input, const wchar_t* output) {
 NifFile donor;
 if (donor.Load(longPath(input))) {
  std::cerr << "Cannot load Skyrim LE donor";
  return 20;
 }
 if (!donor.GetHeader().GetVersion().IsSK()) {
  std::cerr << "Expected a Skyrim LE donor (BS 83)";
  return 21;
 }
 OptOptions options;
 options.targetVersion = NiVersion::getSSE();
 options.removeParallax = false;
 options.fixShaderFlags = false;
 if (donor.OptimizeFor(options).versionMismatch || !donor.GetHeader().GetVersion().IsSSE()) {
  std::cerr << "Skyrim LE to SE conversion failed";
  return 22;
 }
 NifSaveOptions save;
 save.optimize = false;
 save.sortBlocks = false;
 if (donor.Save(longPath(output), save)) {
  std::cerr << "Cannot save converted donor";
  return 23;
 }
 return 0;
}
int wmain(int argc,wchar_t** argv){try{
 if(argc==4 && std::wstring(argv[1])==L"--convert-le")return convertLegacyDonor(argv[2],argv[3]);
 if(argc!=5 && argc!=6)return 2;NifFile dst,src;if(dst.Load(longPath(argv[1])) || src.Load(longPath(argv[2])))return 3;
 if(argc==6){
  unsigned count=0;auto oldShapes=dst.GetShapes();auto donors=src.GetShapes();
  for(auto old:oldShapes){if(old->name.get().rfind("SVC_DarkFill_",0)==0)continue;
   NiShape* matched=nullptr;for(auto donor:donors)if(donor->name==old->name){matched=donor;break;}
   if(!matched || !matched->HasShaderProperty() || !old->ShaderPropertyRef())continue;
   auto clone=dst.CloneShape(matched,"SVR_MaterialDonor",&src);if(!clone)return 14;
   unlinkShape(dst,clone);
   old->ShaderPropertyRef()->index=clone->ShaderPropertyRef()->index;count++;
  }
  if(!count)return 16;NifSaveOptions opt;opt.optimize=false;opt.sortBlocks=false;
  if(dst.Save(longPath(argv[3]),opt))return 15;std::cout<<"material-only="<<count;return 0;
 }
 std::map<std::string,NiNode*> groups;std::map<std::string,unsigned> counts;
 std::ifstream mappings{longPath(argv[4])};std::string line;
 while(std::getline(mappings,line)){auto sep=line.find('\t');if(sep==std::string::npos)return 4;auto original=line.substr(0,sep),physical=line.substr(sep+1);auto node=dst.FindBlockByName<NiNode>(physical);auto donor=src.FindBlockByName<NiNode>(original);if(!node || !donor){std::cout<<"unsupported moving node: "<<original;return 10;}groups[original]=node;counts[original]=0;}
 struct Job{NiShape* shape;NiNode* parent;MatTransform transform;};std::vector<Job> jobs;
 for(auto shape:src.GetShapes()){
  if(shape->IsSkinned()){std::cout<<"skinned donor rejected";return 11;}
  auto parent=dst.GetRootNode();auto node=src.GetParentNode(shape);unsigned depth=0;
  while(node && depth++<128){auto it=groups.find(node->name.get());if(it!=groups.end()){parent=it->second;counts[it->first]++;break;}node=src.GetParentNode(node);}
  auto t=global(dst,parent).InverseTransform().ComposeTransforms(global(src,shape));jobs.push_back({shape,parent,t});
 }
 for(auto& [name,count]:counts)if(!count){std::cout<<"empty moving donor branch: "<<name;return 12;}
 if(jobs.empty())return 13;
 // Unlink old render geometry only. Do not delete/reorder Havok blocks or alter references to them.
 unsigned removed=0;
 for(auto shape:dst.GetShapes()){
  if(shape->name.get().rfind("SVC_DarkFill_",0)==0 || shape->name.get()=="SVC_BarrelInterior")continue;
  unlinkShape(dst,shape);removed++;
 }
 for(auto& job:jobs){auto shape=dst.CloneShape(job.shape,job.shape->name.get(),&src);if(!shape)return 14;shape->controllerRef.Clear();shape->transform=job.transform;dst.SetParentNode(shape,job.parent);}
 NifSaveOptions options;options.optimize=false;options.sortBlocks=false;
 if(dst.Save(longPath(argv[3]),options))return 15;
 std::cout<<"grafted="<<jobs.size()<<" replaced="<<removed;return 0;
 }catch(const std::exception& e){std::cerr<<e.what();return 99;}}

