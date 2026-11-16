// External display harness for the iOS Simulator (tools/ios/external_display_sim/run.sh).
//
// Compiles the production ios/src/external_display.mm (scene delegate, the
// iOS 27 scene accessory and its 1-point window, the grace, the picture's
// view and its pixel cap) and ios/Info.plist.in, with stand-ins for the
// rest: an app delegate that behaves as SDL3's (patched or not), a launcher
// window, then a game window. A test card takes the place of the game's
// picture: drawn with Metal into NFSExternalPictureView, letterboxed with
// external_display_policy.h AspectFit as native_renderer.mm does. Its border
// is the picture's edge and its square stays square unless stretched.
//
// Environment (SIMCTL_CHILD_ prefix through simctl launch):
//   HARNESS_SDL=patched|unpatched   the app delegate (default patched)
//   HARNESS_PLAY=<seconds>          "Play" after this long (default 6)
//   HARNESS_RELEASE=1               at Play the game keeps its picture (emulated renderer)
//   HARNESS_CAP=1080p|1440p|display the External display resolution setting
// Every line it prints starts with "HARNESS" or "[external]".
#import <Metal/Metal.h>
#import <QuartzCore/QuartzCore.h>
#import <UIKit/UIKit.h>

#include <cstdio>
#include <string>

#include "app_scene.h"
#include "external_display.h"

namespace ed = nfsmw::external_display;

static void Say(NSString* format, ...) NS_FORMAT_FUNCTION(1, 2);
static void Say(NSString* format, ...) {
  va_list ap;
  va_start(ap, format);
  NSString* s = [[NSString alloc] initWithFormat:format arguments:ap];
  va_end(ap);
  printf("HARNESS %s\n", s.UTF8String);
  fflush(stdout);
}
static NSString* Env(const char* key, NSString* fallback) {
  const char* v = getenv(key);
  return v && *v ? @(v) : fallback;
}

// ---- the test card -------------------------------------------------------
static id<MTLDevice> g_device;
static id<MTLCommandQueue> g_queue;
static id<MTLRenderPipelineState> g_pso;
static double g_picture_aspect = 16.0 / 9.0;  // the game's shape, chosen at Play

static void MakePipeline() {
  g_device = MTLCreateSystemDefaultDevice();
  g_queue = [g_device newCommandQueue];
  NSString* src = @"#include <metal_stdlib>\nusing namespace metal;\n"
                   "vertex float4 v(uint i [[vertex_id]]) { float2 p = float2((i << 1) & 2, i & 2); return float4(p * 2 - 1, 0, 1); }\n"
                   "fragment float4 f(constant float4& c [[buffer(0)]]) { return c; }\n";
  NSError* error = nil;
  id<MTLLibrary> lib = [g_device newLibraryWithSource:src options:nil error:&error];
  MTLRenderPipelineDescriptor* d = [MTLRenderPipelineDescriptor new];
  d.vertexFunction = [lib newFunctionWithName:@"v"];
  d.fragmentFunction = [lib newFunctionWithName:@"f"];
  d.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
  g_pso = [g_device newRenderPipelineStateWithDescriptor:d error:&error];
  if (!g_pso) Say(@"no pipeline: %@", error);
}

static void Fill(id<MTLRenderCommandEncoder> e, double x, double y, double w, double h, float r, float g, float b) {
  if (w <= 0 || h <= 0) return;
  [e setViewport:(MTLViewport){x, y, w, h, 0, 1}];
  const float c[4] = {r, g, b, 1};
  [e setFragmentBytes:c length:sizeof c atIndex:0];
  [e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
}

static void DrawCard(CAMetalLayer* layer, float tint) {
  id<CAMetalDrawable> d = [layer nextDrawable];
  if (!d || !g_pso) return;
  const double W = d.texture.width, H = d.texture.height;
  const ed::Rect r = ed::AspectFit(g_picture_aspect, W, H);
  MTLRenderPassDescriptor* rp = [MTLRenderPassDescriptor renderPassDescriptor];
  rp.colorAttachments[0].texture = d.texture;
  rp.colorAttachments[0].loadAction = MTLLoadActionClear;
  rp.colorAttachments[0].clearColor = MTLClearColorMake(0, 0, 0, 1);
  rp.colorAttachments[0].storeAction = MTLStoreActionStore;
  id<MTLCommandBuffer> cb = [g_queue commandBuffer];
  id<MTLRenderCommandEncoder> e = [cb renderCommandEncoderWithDescriptor:rp];
  [e setRenderPipelineState:g_pso];
  const double b = std::max(4.0, std::round(r.h / 90));
  Fill(e, r.x, r.y, r.w, r.h, 1, 1, 1);                                        // border
  Fill(e, r.x + b, r.y + b, r.w - 2 * b, r.h - 2 * b, 0.05f, 0.15f * tint, 0.45f);  // picture
  const double side = std::round(r.h * 0.5);                                    // a square: square unless stretched
  Fill(e, r.x + (r.w - side) / 2, r.y + (r.h - side) / 2, side, side, 0.95f, 0.55f, 0.1f);
  [e endEncoding];
  [cb presentDrawable:d];
  [cb commit];
}

// ---- the game stand-in ----------------------------------------------------
static UIWindow* g_launcher;
static UIWindow* g_game;
static UIView* g_phone_picture;  // the phone's picture (native_renderer.mm present_view)
static UILabel* g_caption;
static NFSExternalPictureView* g_external_view;
static UILabel* g_external_info;
static CADisplayLink* g_link;

@interface HarnessTicker : NSObject
@end
@implementation HarnessTicker
- (void)tick:(CADisplayLink*)link {
  static int n;
  ++n;
  if (g_external_view) {
    DrawCard((CAMetalLayer*)g_external_view.layer, 1);
    const CGSize ds = ((CAMetalLayer*)g_external_view.layer).drawableSize;
    UIScreen* s = g_external_view.window.windowScene.screen;
    const ed::Pixels pp = ed::PicturePixels();
    g_external_info.text = [NSString stringWithFormat:@"drawable %.0fx%.0f · display %.0fx%.0f px · picture %.3f:1 · "
                                                       @"resolution follows %@ (%ux%u) · cap %u",
                                                       ds.width, ds.height, s.nativeBounds.size.width,
                                                       s.nativeBounds.size.height, g_picture_aspect,
                                                       ed::SizingExternal() ? @"display" : @"phone", pp.w, pp.h,
                                                       ed::MaxWidth()];
  }
  if (g_phone_picture && g_phone_picture.alpha > 0 && n % 2 == 0) DrawCard((CAMetalLayer*)g_phone_picture.layer, 2);
}
@end
static HarnessTicker* g_ticker;

@interface HarnessMetalView : UIView
@end
@implementation HarnessMetalView
+ (Class)layerClass {
  return CAMetalLayer.class;
}
- (void)layoutSubviews {
  [super layoutSubviews];
  CAMetalLayer* l = (CAMetalLayer*)self.layer;
  const CGFloat s = self.window.windowScene.screen.nativeScale ?: 1;
  l.drawableSize = CGSizeMake(self.bounds.size.width * s, self.bounds.size.height * s);
}
@end

static void Attach(UIView* host) {  // as native_renderer.mm AttachExternalDisplay
  if (g_external_view) {
    [g_external_view removeFromSuperview];
    [g_external_info removeFromSuperview];
    g_external_view = nil;
    g_phone_picture.alpha = 1;
    g_caption.hidden = YES;
    Say(@"picture back on the phone");
  }
  if (!host) return;
  NFSExternalPictureView* v = [[NFSExternalPictureView alloc] initWithFrame:host.bounds];
  v.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
  v.backgroundColor = UIColor.blackColor;
  CAMetalLayer* l = (CAMetalLayer*)v.layer;
  l.device = g_device;
  l.pixelFormat = MTLPixelFormatBGRA8Unorm;
  [host addSubview:v];
  [v layoutIfNeeded];
  g_external_view = v;
  g_external_info = [[UILabel alloc] initWithFrame:CGRectMake(0, 0, host.bounds.size.width, 28)];
  g_external_info.autoresizingMask = UIViewAutoresizingFlexibleWidth;
  g_external_info.textColor = UIColor.yellowColor;
  g_external_info.backgroundColor = [UIColor colorWithWhite:0 alpha:0.6];
  g_external_info.font = [UIFont monospacedSystemFontOfSize:14 weight:UIFontWeightMedium];
  g_external_info.textAlignment = NSTextAlignmentCenter;
  [host addSubview:g_external_info];
  g_phone_picture.alpha = 0;
  g_caption.hidden = NO;
  Say(@"picture on the display: drawable %.0fx%.0f in %.0fx%.0f points", l.drawableSize.width, l.drawableSize.height,
      host.bounds.size.width, host.bounds.size.height);
}

// The lookup touch_controls.mm GameWindow() does: never the 1-point window.
static UIWindow* GameWindowLookup() {
  UIWindow* window = nil;
  for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
    if (!nfsmw::IsAppScene(scene)) continue;
    for (UIWindow* w in ((UIWindowScene*)scene).windows) {
      if (nfsmw::IsHelperWindow(w)) continue;
      if (w.isKeyWindow || !window) window = w;
    }
  }
  return window;
}

static void Play(UIWindowScene* scene) {
  // The shape the game starts in, as settings_catalog.mm ScreenPixels/AutoAspect.
  ed::Pixels px;
  const bool external = ed::ConnectedPixels(&px);
  if (!external) {
    const CGSize n = scene.screen.nativeBounds.size;
    px = ed::Landscape(n.width, n.height);
  }
  const ed::Shape shape = ed::ShapeFor(px.w, px.h);
  g_picture_aspect = shape == ed::Shape::kWide ? ed::WideSceneWidth(px.w, px.h) / 720.0
                     : shape == ed::Shape::k4x3 ? 4.0 / 3.0
                                                : 16.0 / 9.0;
  Say(@"Play: shape %s from the %@'s %ux%u pixels: picture %.3f:1", ed::ShapeName(shape),
      external ? @"display" : @"phone", px.w, px.h, g_picture_aspect);
  // The launcher goes (launcher.mm Run), the game's window comes (SDL's).
  g_launcher.hidden = YES;
  g_launcher.rootViewController = nil;
  g_launcher = nil;
  g_game = [[UIWindow alloc] initWithWindowScene:scene];
  UIViewController* vc = [UIViewController new];
  vc.view.backgroundColor = UIColor.darkGrayColor;
  g_game.rootViewController = vc;
  [g_game makeKeyAndVisible];
  HarnessMetalView* pic = [[HarnessMetalView alloc] initWithFrame:g_game.bounds];
  pic.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
  ((CAMetalLayer*)pic.layer).device = g_device;
  ((CAMetalLayer*)pic.layer).pixelFormat = MTLPixelFormatBGRA8Unorm;
  [g_game insertSubview:pic aboveSubview:vc.view];
  g_phone_picture = pic;
  g_caption = [[UILabel alloc] initWithFrame:CGRectMake(0, g_game.bounds.size.height / 2 - 12, g_game.bounds.size.width, 24)];
  g_caption.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleTopMargin |
                               UIViewAutoresizingFlexibleBottomMargin;
  g_caption.text = @"Playing on the external display";
  g_caption.textAlignment = NSTextAlignmentCenter;
  g_caption.textColor = [UIColor colorWithWhite:0.6 alpha:1];
  g_caption.hidden = YES;
  [g_game insertSubview:g_caption aboveSubview:pic];
  UILabel* pad = [[UILabel alloc] initWithFrame:CGRectMake(20, 20, 160, 44)];  // the touch controls' stand-in
  pad.text = @"[ touch controls ]";
  pad.textColor = UIColor.whiteColor;
  [g_game addSubview:pad];
  UIWindow* found = GameWindowLookup();
  Say(@"game window lookup: %@ (%@)", found == g_game ? @"the game's window" : @"ANOTHER WINDOW",
      nfsmw::IsHelperWindow(found) ? @"the 1-point window: WRONG" : @"not the 1-point window");
  if ([Env("HARNESS_RELEASE", @"0") isEqualToString:@"1"]) {
    ed::Release();
    Say(@"released: the display should mirror the phone");
    return;
  }
  ed::SetPictureHandler([](UIView* host) { Attach(host); });
}

// ---- SDL3's app delegate, as it behaves --------------------------------------
static int g_main_calls = 0;

@interface HarnessSDLDelegate : NSObject <UIApplicationDelegate, UIWindowSceneDelegate>
@end
@implementation HarnessSDLDelegate
- (UISceneConfiguration*)application:(UIApplication*)application
    configurationForConnectingSceneSession:(UISceneSession*)session
                                   options:(UISceneConnectionOptions*)options {
  const bool patched = ![Env("HARNESS_SDL", @"patched") isEqualToString:@"unpatched"];
  Say(@"app delegate asked for role %@ (%@)", session.role, patched ? @"patched SDL" : @"unpatched SDL");
  if (patched && ![session.role isEqualToString:UIWindowSceneSessionRoleApplication]) return session.configuration;
  UISceneConfiguration* c = [[UISceneConfiguration alloc] initWithName:@"SDLSceneConfiguration" sessionRole:session.role];
  c.delegateClass = HarnessSDLDelegate.class;
  return c;
}
- (void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)o {
  scene.delegate = self;
  ++g_main_calls;
  Say(@"SDL's delegate connected a scene of role %@: main() call %d%@", session.role, g_main_calls,
      g_main_calls > 1 ? @" (A SECOND MAIN: the bug the SDL patch fixes)" : @"");
  if (g_main_calls > 1) return;
  UIWindowScene* ws = (UIWindowScene*)scene;
  dispatch_async(dispatch_get_main_queue(), ^{  // SDL's postFinishLaunch: main() runs the launcher
    MakePipeline();
    ed::SetLog([](const std::string& line) {
      printf("%s\n", line.c_str());
      fflush(stdout);
    });
    NSString* cap = Env("HARNESS_CAP", @"1080p");
    ed::SetMaxWidth(ed::MaxWidthFor(cap.UTF8String));
    g_launcher = [[UIWindow alloc] initWithWindowScene:ws];
    UIViewController* vc = [UIViewController new];
    vc.view.backgroundColor = UIColor.systemIndigoColor;
    UILabel* l = [[UILabel alloc] initWithFrame:vc.view.bounds];
    l.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    l.text = @"LAUNCHER (stand-in)";
    l.textAlignment = NSTextAlignmentCenter;
    l.textColor = UIColor.whiteColor;
    [vc.view addSubview:l];
    g_launcher.rootViewController = vc;
    g_launcher.windowLevel = UIWindowLevelNormal + 1;
    [g_launcher makeKeyAndVisible];
    ed::Start();
    Say(@"launcher up; External display resolution %@ (at most %u across)", cap, ed::MaxWidth());
    g_ticker = [HarnessTicker new];
    g_link = [CADisplayLink displayLinkWithTarget:g_ticker selector:@selector(tick:)];
    g_link.preferredFrameRateRange = CAFrameRateRangeMake(30, 30, 30);
    [g_link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
    const double play = Env("HARNESS_PLAY", @"6").doubleValue;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, int64_t(play * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
      Play(ws);
    });
  });
}
- (void)sceneDidBecomeActive:(UIScene*)scene {
  Say(@"app scene active");
}
- (void)sceneDidEnterBackground:(UIScene*)scene {
  Say(@"app scene in the background");
}
@end

int main(int argc, char* argv[]) {
  @autoreleasepool {
    Say(@"start (SDL %@)", Env("HARNESS_SDL", @"patched"));
    return UIApplicationMain(argc, argv, nil, @"HarnessSDLDelegate");
  }
}
