// Host-only feasibility fixture. No game hooks, caches, flags or shader edits.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <simd/simd.h>
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

struct Vertex { simd_float4 position, color, uv, normal; };
struct Push { uint64_t vs, ps, shared, previous; };
struct Draw {
  id<MTLBuffer> vertices, indices, vs, ps, shared;
  NSUInteger count;
  int material;
  bool candidate, edge, barrier=false, color=true, less=false;
};
struct Material { id<MTLLibrary> vs, ps; id<MTLRenderPipelineState> opaque, edge, depth, plain; };
struct Target { id<MTLTexture> color, depth; };
static id<MTLDevice> device;
static id<MTLCommandQueue> queue;
static Material materials[2];
static id<MTLBuffer> heap, samplers;
static id<MTLTexture> diffuse, shadow_texture;
static id<MTLSamplerState> sampler;
static id<MTLDepthStencilState> leWrite, lessRead, equalRead, strictWrite;
static NSArray* configs;
static uint64_t comparisons=0, pixels=0;
static id<MTLBuffer> Buffer(NSUInteger n) { return [device newBufferWithLength:n options:MTLResourceStorageModeShared]; }
static id<MTLLibrary> Library(NSString* path) {
 NSError* error=nil; id<MTLLibrary> lib=[device newLibraryWithURL:[NSURL fileURLWithPath:path] error:&error];
 if(!lib) NSLog(@"%@",error); assert(lib); return lib;
}
static id<MTLFunction> Function(id<MTLLibrary> lib,NSString* name,uint32_t spec) {
 MTLFunctionConstantValues* v=[MTLFunctionConstantValues new]; bool gather=true;
 [v setConstantValue:&spec type:MTLDataTypeUInt atIndex:0]; [v setConstantValue:&gather type:MTLDataTypeBool atIndex:1];
 NSError* error=nil; id<MTLFunction> f=[lib newFunctionWithName:name constantValues:v error:&error];
 if(!f) NSLog(@"%@",error); assert(f); return f;
}
static id<MTLRenderPipelineState> Pipeline(int m,int mode) {
 NSDictionary* cfg=configs[m]; uint32_t spec=(mode==1?0x102u:0x602u) | (m?0x2000u:0);
 if(mode==3) spec=0;
 id<MTLFunction> vs=Function(materials[m].vs,[@"nfsmw_" stringByAppendingString:cfg[@"vs"]],0);
 id<MTLFunction> ps=Function(materials[m].ps,mode==2?@"foliage_depth":[@"nfsmw_" stringByAppendingString:cfg[@"ps"]],spec);
 MTLRenderPipelineDescriptor* pd=[MTLRenderPipelineDescriptor new]; pd.vertexFunction=vs; pd.fragmentFunction=ps;
 pd.colorAttachments[0].pixelFormat=MTLPixelFormatRGBA8Unorm; pd.depthAttachmentPixelFormat=MTLPixelFormatDepth32Float;
 pd.colorAttachments[0].writeMask=mode==2?MTLColorWriteMaskNone:MTLColorWriteMaskAll;
 if(mode==1) {
  auto c=pd.colorAttachments[0];c.blendingEnabled=YES;
  c.sourceRGBBlendFactor=c.sourceAlphaBlendFactor=MTLBlendFactorSourceAlpha;
  c.destinationRGBBlendFactor=c.destinationAlphaBlendFactor=MTLBlendFactorOneMinusSourceAlpha;
 }
 MTLVertexDescriptor* vd=[MTLVertexDescriptor vertexDescriptor];
 for(MTLVertexAttribute* a in vs.vertexAttributes) {
  if(!a.active) continue;
  assert(a.attributeType==MTLDataTypeFloat4);
  NSUInteger offset=a.attributeIndex==0?0:a.attributeIndex==17?16:a.attributeIndex==13?32:48;
  assert(a.attributeIndex==0 || a.attributeIndex==17 || a.attributeIndex==13 || a.attributeIndex==4);
  vd.attributes[a.attributeIndex].format=MTLVertexFormatFloat4;vd.attributes[a.attributeIndex].offset=offset;vd.attributes[a.attributeIndex].bufferIndex=9;
 }
 vd.layouts[9].stride=sizeof(Vertex); pd.vertexDescriptor=vd;
 NSError* error=nil;id<MTLRenderPipelineState> p=[device newRenderPipelineStateWithDescriptor:pd error:&error];
 if(!p) NSLog(@"%@",error); assert(p); return p;
}
static id<MTLDepthStencilState> Depth(MTLCompareFunction cmp,bool write) {
 MTLDepthStencilDescriptor* d=[MTLDepthStencilDescriptor new];d.depthCompareFunction=cmp;d.depthWriteEnabled=write;
 return [device newDepthStencilStateWithDescriptor:d];
}
static void InitVS(id<MTLBuffer> buffer,int m,bool lights) {
 float* f=(float*)buffer.contents;
 for(int i=0;i<1024;++i)f[i]=.1f;
 NSDictionary* cfg=configs[m]; NSDictionary* matrices=cfg[@"matrices"];
 for(NSString* key in matrices) {
  unsigned at=[matrices[key] unsignedIntValue]*4;
  if(at+16>1024)continue;
  for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c)f[at+r*4+c]=(r==c);
  if([key isEqualToString:@"matShadowMapWVP"]) {
   const float matrix[16]={.45f,0,0,.5f,0,-.45f,0,.5f,0,0,0,.5f,0,0,0,1};std::memcpy(f+at,matrix,sizeof(matrix));
  }
 }
 NSDictionary* offsets=cfg[@"offsets"];
 for(NSString* key in offsets) {
  float* v=f+[offsets[key] unsignedIntValue]/4;
  if([key hasPrefix:@"ActiveAuxiliary"]) {v[0]=lights?1:0;}
  if([key isEqualToString:@"LightDirVec"]) {v[0]=.2f;v[1]=.4f;v[2]=.9f;v[3]=0;}
  if([key isEqualToString:@"LocalEyePos"]) {v[0]=0;v[1]=0;v[2]=2;v[3]=1;}
  if([key isEqualToString:@"Fog_DistanceScale"]) {v[0]=.05f;}
  if([key isEqualToString:@"kMaxDist"]) {v[0]=1;}
 }
}
static Target MakeTarget(unsigned w,unsigned h) {
 auto c=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:w height:h mipmapped:NO];
 c.usage=MTLTextureUsageRenderTarget|MTLTextureUsageShaderRead;c.storageMode=MTLStorageModePrivate;
 auto d=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatDepth32Float width:w height:h mipmapped:NO];
 d.usage=MTLTextureUsageRenderTarget;d.storageMode=MTLStorageModePrivate;
 return {[device newTextureWithDescriptor:c],[device newTextureWithDescriptor:d]};
}
static void Texture(unsigned pattern,bool linear) {
 MTLSamplerDescriptor* sd=[MTLSamplerDescriptor new];sd.supportArgumentBuffers=YES;
 sd.minFilter=sd.magFilter=linear?MTLSamplerMinMagFilterLinear:MTLSamplerMinMagFilterNearest;
 sd.mipFilter=linear?MTLSamplerMipFilterLinear:MTLSamplerMipFilterNearest;
 sd.sAddressMode=sd.tAddressMode=MTLSamplerAddressModeRepeat;sampler=[device newSamplerStateWithDescriptor:sd];
 const unsigned size=64;std::vector<uint8_t> rgba(size*size*4);std::vector<float> depths(size*size);
 for(unsigned y=0;y<size;++y)for(unsigned x=0;x<size;++x) {
  unsigned i=y*size+x;rgba[4*i]=30+(x*3)%220;rgba[4*i+1]=45+(y*2)%200;rgba[4*i+2]=90;
  rgba[4*i+3]=pattern==0?255:pattern==1?((x/4+y/4)%2?255:0):uint8_t((x*11+y*17)%256);
  depths[i]=.2f+.6f*float((x*3+y*5)%64)/63;
 }
 auto td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:size height:size mipmapped:YES];
 td.usage=MTLTextureUsageShaderRead;td.storageMode=MTLStorageModeShared;diffuse=[device newTextureWithDescriptor:td];
 [diffuse replaceRegion:MTLRegionMake2D(0,0,size,size) mipmapLevel:0 withBytes:rgba.data() bytesPerRow:size*4];
 unsigned levelSize=size;
 for(unsigned level=1;level<diffuse.mipmapLevelCount;++level) {
  unsigned next=levelSize/2;std::vector<uint8_t> mip(next*next*4);
  for(unsigned y=0;y<next;++y)for(unsigned x=0;x<next;++x)for(unsigned c=0;c<4;++c) {
   unsigned sum=0;for(unsigned oy=0;oy<2;++oy)for(unsigned ox=0;ox<2;++ox)sum+=rgba[((y*2+oy)*levelSize+x*2+ox)*4+c];
   mip[(y*next+x)*4+c]=uint8_t((sum+2)/4);
  }
  [diffuse replaceRegion:MTLRegionMake2D(0,0,next,next) mipmapLevel:level withBytes:mip.data() bytesPerRow:next*4];rgba=std::move(mip);levelSize=next;
 }
 td.pixelFormat=MTLPixelFormatR32Float;td.mipmapLevelCount=1;shadow_texture=[device newTextureWithDescriptor:td];
 [shadow_texture replaceRegion:MTLRegionMake2D(0,0,size,size) mipmapLevel:0 withBytes:depths.data() bytesPerRow:size*4];
 heap=Buffer(16);uint64_t ids[2]={diffuse.gpuResourceID._impl,shadow_texture.gpuResourceID._impl};std::memcpy(heap.contents,ids,16);
 samplers=Buffer(16);uint64_t sids[2]={sampler.gpuResourceID._impl,sampler.gpuResourceID._impl};std::memcpy(samplers.contents,sids,16);
}
static std::vector<Draw> Scene(int material,unsigned layers,unsigned grid,int order,bool mixed,bool lights,bool shadows,bool fenceAlpha,bool perspective=false) {
 std::vector<Draw> out;
 for(unsigned k=0;k<layers;++k) {
  float z=order==0?.9f-.8f*float(k)/std::max(layers-1u,1u):order==1?.1f+.8f*float(k)/std::max(layers-1u,1u):.5f;
  int m=mixed?int(k%2):material; bool candidate=!(m==1 && !fenceAlpha);
  auto vb=Buffer((grid+1)*(grid+1)*sizeof(Vertex));auto verts=(Vertex*)vb.contents;
  float dx=order==2?float(k%3)*.017f:float(k%4)*.02f;
  for(unsigned y=0;y<=grid;++y)for(unsigned x=0;x<=grid;++x) {
   float u=float(x)/grid,v=float(y)/grid;verts[y*(grid+1)+x]={{-.94f+1.8f*u+dx,-.9f+1.8f*v,z,1},{.8f,.9f,.6f,.9f},{u*2.3f+float(k%3)*.13f,v*2.1f,0,0},{0,0,1,0}};
  }
  auto ib=Buffer(grid*grid*6*sizeof(uint32_t));auto idx=(uint32_t*)ib.contents;unsigned at=0;
  for(unsigned y=0;y<grid;++y)for(unsigned x=0;x<grid;++x) {unsigned a=y*(grid+1)+x,b=a+1,c=a+grid+1,d=c+1;for(unsigned q:{a,b,c,b,d,c})idx[at++]=q;}
  auto vs=Buffer(4096);InitVS(vs,m,lights);
  if(perspective) {
   unsigned base=[configs[m][@"matrices"][@"WorldViewProj"] unsignedIntValue]*4;
   const float matrix[16]={.87f,.13f,.07f,.03f,-.11f,.91f,.05f,.01f,.017f,-.013f,.77f,.05f,.123f,.07f,.021f,1};
   std::memcpy((float*)vs.contents+base,matrix,sizeof(matrix));
  }
  auto ps=Buffer(4096);std::memset(ps.contents,0,4096);
  float* pf=(float*)ps.contents;pf[0]=pf[1]=pf[2]=pf[3]=m?1:.15f;if(m){pf[4]=.001f;pf[8]=shadows?1:0;}
  auto sh=Buffer(384);std::memset(sh.contents,0,384);((uint32_t*)sh.contents)[1]=1;float threshold=.706f;std::memcpy((char*)sh.contents+372,&threshold,4);
  out.push_back({vb,ib,vs,ps,sh,at,m,candidate,false});
  if(candidate) {Draw edge=out.back();edge.candidate=false;edge.edge=true;out.push_back(edge);}
 }
 return out;
}
static void DrawOne(id<MTLRenderCommandEncoder> enc,const Draw& d,int phase) {
 Material& m=materials[d.material];
 id<MTLRenderPipelineState> p=phase==1?m.depth:d.edge?m.edge:(!d.candidate?m.plain:m.opaque);
 if(!d.color)p=m.depth;
 [enc setRenderPipelineState:p];
 [enc setDepthStencilState:phase==1?leWrite:d.edge?lessRead:phase==2?equalRead:d.less?strictWrite:leWrite];
 [enc setVertexBuffer:d.vertices offset:0 atIndex:9];
 Push push{d.vs.gpuAddress,d.ps.gpuAddress,d.shared.gpuAddress,0};
 [enc setVertexBytes:&push length:sizeof(push) atIndex:8];[enc setFragmentBytes:&push length:sizeof(push) atIndex:8];
 [enc setFragmentBuffer:heap offset:0 atIndex:0];[enc setFragmentBuffer:samplers offset:0 atIndex:4];
 [enc useResource:d.vs usage:MTLResourceUsageRead stages:MTLRenderStageVertex];
 [enc useResource:d.ps usage:MTLResourceUsageRead stages:MTLRenderStageFragment];
 [enc useResource:d.shared usage:MTLResourceUsageRead stages:MTLRenderStageVertex|MTLRenderStageFragment];
 [enc drawIndexedPrimitives:MTLPrimitiveTypeTriangle indexCount:d.count indexType:MTLIndexTypeUInt32 indexBuffer:d.indices indexBufferOffset:0];
}
static bool Boundary(const Draw& d) {
 return d.barrier || !d.color || d.less;
}
static void Encode(id<MTLCommandBuffer> cb,Target t,const std::vector<Draw>& draws,bool candidate) {
 MTLRenderPassDescriptor* rp=[MTLRenderPassDescriptor renderPassDescriptor];rp.colorAttachments[0].texture=t.color;
 rp.colorAttachments[0].loadAction=MTLLoadActionClear;rp.colorAttachments[0].storeAction=MTLStoreActionStore;rp.colorAttachments[0].clearColor=MTLClearColorMake(.04,.15,.38,.78);
 rp.depthAttachment.texture=t.depth;rp.depthAttachment.loadAction=MTLLoadActionClear;rp.depthAttachment.storeAction=MTLStoreActionStore;rp.depthAttachment.clearDepth=1;
 id<MTLRenderCommandEncoder> enc=[cb renderCommandEncoderWithDescriptor:rp];
 [enc useResource:diffuse usage:MTLResourceUsageRead stages:MTLRenderStageFragment];[enc useResource:shadow_texture usage:MTLResourceUsageRead stages:MTLRenderStageFragment];
 // Model boundaries only. A production collector must additionally classify
 // queries, stencil, MRT, motion, resolves, clears and unsupported draw states.
 size_t i=0;
 while(i<draws.size()) {
  if(Boundary(draws[i])){DrawOne(enc,draws[i],0);++i;continue;}
  size_t end=i;while(end<draws.size()&&!Boundary(draws[end]))++end;
  if(candidate)for(size_t k=i;k<end;++k)if(draws[k].candidate)DrawOne(enc,draws[k],1);
  for(size_t k=i;k<end;++k)DrawOne(enc,draws[k],candidate&&draws[k].candidate?2:0);
  i=end;
 }
 [enc endEncoding];
}
struct Image { std::vector<uint8_t> color, depth; };
static Image Read(Target t,const std::vector<Draw>& draws,bool candidate) {
 auto cb=[queue commandBuffer];Encode(cb,t,draws,candidate);unsigned w=(unsigned)t.color.width,h=(unsigned)t.color.height;NSUInteger row=(w*4+255)&~255u;
 auto a=Buffer(row*h),b=Buffer(row*h);auto blit=[cb blitCommandEncoder];
 for(unsigned i=0;i<2;++i)[blit copyFromTexture:i?t.depth:t.color sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0) sourceSize:MTLSizeMake(w,h,1) toBuffer:i?b:a destinationOffset:0 destinationBytesPerRow:row destinationBytesPerImage:row*h];
 [blit endEncoding];[cb commit];[cb waitUntilCompleted];assert(cb.status==MTLCommandBufferStatusCompleted);
 Image out;out.color.resize(w*h*4);out.depth.resize(w*h*4);
 for(unsigned y=0;y<h;++y){std::memcpy(out.color.data()+y*w*4,(char*)a.contents+y*row,w*4);std::memcpy(out.depth.data()+y*w*4,(char*)b.contents+y*row,w*4);}
 return out;
}
static bool Check(Target t,const std::vector<Draw>& draws,NSString* label,NSString* output) {
 Image a=Read(t,draws,false),b=Read(t,draws,true);++comparisons;pixels+=t.color.width*t.color.height;
  size_t depthPixels=0;
  for(size_t i=0;i<a.depth.size();i+=4) {uint32_t z;std::memcpy(&z,a.depth.data()+i,4);depthPixels+=z!=0x3f800000u;}
  size_t colorPixels=0;const uint8_t clear[4]={10,38,97,199};
  for(size_t i=0;i<a.color.size();i+=4)colorPixels+=std::memcmp(a.color.data()+i,clear,4)!=0;
  // Minified foliage can legitimately have only blended edges and clear depth.
  assert(depthPixels>t.color.width*t.color.height/100 || colorPixels>t.color.width*t.color.height/100);

 if(a.color!=b.color || a.depth!=b.depth) {
  NSUInteger cd=0,dd=0;for(size_t i=0;i<a.color.size();++i){cd+=a.color[i]!=b.color[i];dd+=a.depth[i]!=b.depth[i];}
  printf("FAIL %s color bytes %lu depth bytes %lu\n",label.UTF8String,(unsigned long)cd,(unsigned long)dd);
  [[NSData dataWithBytes:a.color.data() length:a.color.size()] writeToFile:[output stringByAppendingPathComponent:@"reference.rgba"] atomically:YES];
  [[NSData dataWithBytes:b.color.data() length:b.color.size()] writeToFile:[output stringByAppendingPathComponent:@"candidate.rgba"] atomically:YES];
  return false;
 }
 return true;
}
static double Median(std::vector<double> v){std::sort(v.begin(),v.end());return v[v.size()/2];}
static std::pair<double,double> Cost(Target t,const std::vector<Draw>& draws,bool candidate,unsigned frames) {
 auto cb=[queue commandBuffer];auto begin=std::chrono::steady_clock::now();
 for(unsigned i=0;i<frames;++i)Encode(cb,t,draws,candidate);
 auto end=std::chrono::steady_clock::now();[cb commit];[cb waitUntilCompleted];assert(cb.status==MTLCommandBufferStatusCompleted);
 return {(cb.GPUEndTime-cb.GPUStartTime)*1000/frames,std::chrono::duration<double,std::milli>(end-begin).count()/frames};
}
int main(int argc,const char** argv) {
 @autoreleasepool {
  assert(argc==3);NSString* output=@(argv[1]);bool benchmark=strcmp(argv[2],"benchmark")==0;
  device=MTLCreateSystemDefaultDevice();assert(device);queue=[device newCommandQueue];
  NSError* error=nil;configs=[NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:[output stringByAppendingPathComponent:@"config.json"]] options:0 error:&error];assert(configs.count==2);
  printf("DEVICE %s\n",device.name.UTF8String);
  for(int m=0;m<2;++m) {
   materials[m].vs=Library([output stringByAppendingPathComponent:[configs[m][@"vs"] stringByAppendingString:@".metallib"]]);
   materials[m].ps=Library([output stringByAppendingPathComponent:[configs[m][@"ps"] stringByAppendingString:@".metallib"]]);
   materials[m].opaque=Pipeline(m,0);materials[m].edge=Pipeline(m,1);materials[m].depth=Pipeline(m,2);materials[m].plain=Pipeline(m,3);
  }
  leWrite=Depth(MTLCompareFunctionLessEqual,true);lessRead=Depth(MTLCompareFunctionLess,false);equalRead=Depth(MTLCompareFunctionEqual,false);strictWrite=Depth(MTLCompareFunctionLess,true);
  unsigned cases=0;
  for(int m=0;m<2;++m)for(int order=0;order<3;++order)for(unsigned pattern:{0u,1u,2u})for(bool linear:{false,true}) {
   @autoreleasepool {
    Texture(pattern,linear);auto t=MakeTarget(192,128);auto draws=Scene(m,8,order==2?8:1,order,false,true,true,true);
    NSString* name=[NSString stringWithFormat:@"material%d order%d alpha%u filter%d",m,order,pattern,linear];
    if(!Check(t,draws,name,output))return 2;++cases;
   }
  }
  // Mixed material order, an ordinary opaque non-candidate, and explicit depth-only barriers.
  for(int order=0;order<3;++order){Texture(2,true);auto t=MakeTarget(192,128);auto draws=Scene(0,12,8,order,true,true,true,false);if(!Check(t,draws,@"mixed/fallback",output))return 2;++cases;
   Draw barrier=draws[draws.size()/2];barrier.candidate=false;barrier.edge=false;barrier.color=false;draws.insert(draws.begin()+draws.size()/2,barrier);
   if(!Check(t,draws,@"depth-only barrier",output))return 2;++cases;
   auto strict=Scene(0,8,8,order,false,true,true,true);strict[4].less=true;
   if(!Check(t,strict,@"strict LESS write boundary",output))return 2;++cases;
  }
  for(int m=0;m<2;++m)for(int order=0;order<3;++order) {
   Texture(2,true);auto t=MakeTarget(192,128);auto draws=Scene(m,8,8,order,false,true,true,true,true);
   if(!Check(t,draws,@"perspective and equal-depth precision",output))return 2;++cases;
  }
  for(bool lights:{false,true})for(bool alpha:{false,true}) {
   Texture(2,true);auto t=MakeTarget(192,128);auto draws=Scene(1,8,8,0,false,lights,false,alpha,true);
   if(!Check(t,draws,@"shadow-disabled and alpha-disabled controls",output))return 2;++cases;
  }
  for(int m=0;m<2;++m)for(int order=0;order<3;++order)for(bool linear:{false,true})for(float threshold:{.392f,.706f}) {
   Texture(2,linear);auto t=MakeTarget(48,32);auto draws=Scene(m,8,8,order,false,true,true,true,true);
   for(Draw& d:draws) {
    std::memcpy((char*)d.shared.contents+372,&threshold,4);
    if(!d.edge) {auto indices=(uint32_t*)d.indices.contents;for(NSUInteger i=0;i<d.count;i+=3)std::swap(indices[i],indices[i+1]);}
   }
   if(!Check(t,draws,@"minified mipmaps, alternate threshold and opposite winding",output))return 2;++cases;
  }
  printf("PASS %u image cases, %llu exact RGBA/depth comparisons, %llu pixels\n",cases,(unsigned long long)comparisons,(unsigned long long)pixels);
  if(!benchmark)return 0;
  NSMutableArray* results=[NSMutableArray new];
  // Models 0/1 are eligible tree/fence stress cases. 2 is mixed with ordinary
  // non-alpha-tested fences; 3 disables shadows; 4 admits no candidate at all.
  for(int model=0;model<5;++model)for(unsigned layers:{1u,8u,24u})for(unsigned grid:{1u,8u})for(int order:{0,1}) {
   if(model>=2 && (layers==1 || grid!=8))continue;
   @autoreleasepool {
    int m=model==0?0:1;
    Texture(2,true);Target t=MakeTarget(960,540);auto draws=Scene(m,layers,grid,order,model==2,true,model!=3,model<2 || model==3);
    auto warm=Cost(t,draws,false,4);Cost(t,draws,true,4);
    // Long enough to expose timing noise with the identical-stream control,
    // rather than inferring small wins from sub-millisecond command buffers.
    unsigned frames=std::clamp(unsigned(std::ceil(20.0/std::max(warm.first,.001))),4u,512u);
    std::vector<double>a,b,ac,bc;NSMutableArray* trials=[NSMutableArray new];
    for(unsigned trial=0;trial<7;++trial){bool first=trial%2;auto x=Cost(t,draws,first,frames),y=Cost(t,draws,!first,frames);auto ref=first?y:x,cand=first?x:y;a.push_back(ref.first);b.push_back(cand.first);ac.push_back(ref.second);bc.push_back(cand.second);[trials addObject:@{@"reference_gpu_ms":@(ref.first),@"candidate_gpu_ms":@(cand.first)}];}
    double ref=Median(a),cand=Median(b);
    NSDictionary* r=@{@"model":@(model),@"material":@(m),@"layers":@(layers),@"grid":@(grid),@"order":@(order),@"frames_per_batch":@(frames),@"reference_gpu_ms":@(ref),@"candidate_gpu_ms":@(cand),@"gpu_delta_pct":@((cand/ref-1)*100),@"reference_encode_ms":@(Median(ac)),@"candidate_encode_ms":@(Median(bc)),@"trials":trials};[results addObject:r];
    printf("COST model%d layers%u grid%u order%d %.4f -> %.4f ms (%+.2f%%)\n",model,layers,grid,order,ref,cand,(cand/ref-1)*100);fflush(stdout);
   }
  }
  [[NSJSONSerialization dataWithJSONObject:results options:NSJSONWritingPrettyPrinted error:nil] writeToFile:[output stringByAppendingPathComponent:@"costs.json"] atomically:YES];
 }
}
