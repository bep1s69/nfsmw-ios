// NFSMW Recompiled (iOS) - an external display: its scene, its window, the
// picture's place on it. See external_display.h.

#import <QuartzCore/QuartzCore.h>
#import <UIKit/UIKit.h>

#include <atomic>
#include <cstdio>

#include "app_scene.h"
#include "boot_trace.h"
#include "external_display.h"

namespace ed = nfsmw::external_display;

namespace {

std::function<void(const std::string&)> g_log;
void Log(const char* format, ...) __attribute__((format(printf, 1, 2)));
void Log(const char* format, ...) {
  char line[512];
  va_list ap;
  va_start(ap, format);
  vsnprintf(line, sizeof line, format, ap);
  va_end(ap);
  const std::string text = std::string("[external] ") + line;
  if (g_log) {
    g_log(text);
  } else {
    nfsmw::boot::Trace(text);
  }
}

std::atomic<uint32_t> g_max_width{ed::kDefaultMaxWidth};
std::atomic<uint32_t> g_pixels_w{0}, g_pixels_h{0};
std::atomic<bool> g_sizing_external{false};

ed::Router g_router;
std::function<void(UIView*)> g_handler;
UIWindow* g_window = nil;      // on the display's scene, while one is connected
UIView* g_given = nil;         // the host view the handler was last given
bool g_released = false;       // Release(): the display mirrors the phone
bool g_started = false;
int g_settle_generation = 0;
id g_registration = nil;       // UISceneAccessoryRegistration (iOS 27)
UIWindow* g_anchor = nil;      // holds g_registration's view controller

double Now() { return CACurrentMediaTime(); }

void Publish() {
  g_sizing_external.store(g_router.sizing_external(), std::memory_order_release);
}

void Settle();

// Asks the router again when it says, and once more on each activation.
void ScheduleSettle() {
  const double in = g_router.SettleIn(Now());
  const int generation = ++g_settle_generation;
  if (in < 0) return;
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, int64_t((in + 0.01) * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
    if (generation == g_settle_generation) Settle();
  });
}

void Settle() {
  if (g_router.Settle(Now())) {
    Publish();
    Log("the display stayed away %.0f s with the app active: the resolution follows the phone again",
        ed::Router::kGraceSeconds);
  }
  ScheduleSettle();
}

// The display's pixels for the picture, from its window (on layout).
void UpdatePixels(UIView* view) {
  UIScreen* screen = view.window.windowScene.screen;
  const CGFloat scale = screen.nativeScale > 0 ? screen.nativeScale : (screen.scale > 0 ? screen.scale : 1.0);
  const CGSize size = view.bounds.size;
  if (size.width < 1 || size.height < 1) return;
  const ed::Pixels p = ed::CappedPixels(size.width * scale, size.height * scale, g_max_width.load());
  if (p.w == g_pixels_w.load() && p.h == g_pixels_h.load()) return;
  g_pixels_w = p.w;
  g_pixels_h = p.h;
  Log("the display's picture: %ux%u pixels (the display %.0fx%.0f, %.0fx%.0f points at %.2f, up to %ld Hz; at most %u across)",
      p.w, p.h, screen.nativeBounds.size.width, screen.nativeBounds.size.height, size.width, size.height, scale,
      long(screen.maximumFramesPerSecond), g_max_width.load());
}

void GiveHost() {
  UIView* host = (g_window && !g_released) ? g_window.rootViewController.view : nil;
  if (host == g_given) return;
  g_given = host;
  if (g_handler) g_handler(host);
}

}  // namespace

// The display's content: black, with a short note until the game's picture
// covers it (the launcher, the first frames).
@interface NFSExternalDisplayController : UIViewController
@end

@implementation NFSExternalDisplayController {
  UILabel* _note;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.view.backgroundColor = UIColor.blackColor;
  _note = [UILabel new];
  _note.numberOfLines = 0;
  _note.textAlignment = NSTextAlignmentCenter;
  _note.textColor = [UIColor colorWithWhite:0.75 alpha:1.0];
  _note.font = [UIFont systemFontOfSize:28 weight:UIFontWeightSemibold];
  _note.text = @"Need for Speed: Most Wanted\n\nThe game appears here when it starts.";
  _note.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:_note];
  [NSLayoutConstraint activateConstraints:@[
    [_note.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
    [_note.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor],
    [_note.widthAnchor constraintLessThanOrEqualToAnchor:self.view.widthAnchor multiplier:0.8],
  ]];
}

- (void)viewDidLayoutSubviews {
  [super viewDidLayoutSubviews];
  UpdatePixels(self.view);
}

@end

// The picture's view (external_display.h): a 4K drawable costs about four
// times the GPU time of 1080p for a 720p-1440p game picture and has come out
// black over AirPlay, so 1920 across by default.
@implementation NFSExternalPictureView
+ (Class)layerClass {
  return CAMetalLayer.class;
}
- (void)didMoveToWindow {
  [super didMoveToWindow];
  [self setNeedsLayout];
}
- (void)layoutSubviews {
  [super layoutSubviews];
  CAMetalLayer* layer = (CAMetalLayer*)self.layer;
  UIScreen* screen = self.window.windowScene.screen;
  const CGFloat scale = screen.nativeScale > 0 ? screen.nativeScale : 1.0;
  const CGSize size = self.bounds.size;
  const ed::Pixels p = ed::CappedPixels(size.width * scale, size.height * scale, g_max_width.load());
  if (!p.w || !p.h) return;
  // Displays are landscape; a portrait one gets its long side down.
  const bool landscape = size.width >= size.height;
  layer.contentsScale = CGFloat(landscape ? p.w : p.h) / size.width;
  layer.drawableSize = landscape ? CGSizeMake(p.w, p.h) : CGSizeMake(p.h, p.w);
}
@end

// The display's scene (named in Info.plist for iOS 17-26, and in the scene
// accessory's configuration for iOS 27).
@interface NFSExternalDisplaySceneDelegate : UIResponder <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow* window;
@end

@implementation NFSExternalDisplaySceneDelegate

- (void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options {
  if (![scene isKindOfClass:UIWindowScene.class]) return;
  UIWindowScene* ws = (UIWindowScene*)scene;
  UIScreen* screen = ws.screen;
  Log("a display's scene connected: %.0fx%.0f pixels, %.0fx%.0f points at %.2f, up to %ld Hz%s",
      screen.nativeBounds.size.width, screen.nativeBounds.size.height, screen.bounds.size.width,
      screen.bounds.size.height, screen.nativeScale, long(screen.maximumFramesPerSecond),
      g_window ? " (another display already shows the game: this one mirrors the phone)" : "");
  // One display at a time, and none after Release(): without a window of
  // ours iOS mirrors the phone there.
  if (g_window || g_released) return;
  // A window, not key: the phone's window keeps the keyboard and the focus.
  self.window = [[UIWindow alloc] initWithWindowScene:ws];
  self.window.rootViewController = [NFSExternalDisplayController new];
  self.window.hidden = NO;
  [self.window.rootViewController.view setNeedsLayout];
  [self.window.rootViewController.view layoutIfNeeded];
  g_window = self.window;
  g_router.Connect(Now());
  Publish();
  ScheduleSettle();
  GiveHost();
}

- (void)sceneDidDisconnect:(UIScene*)scene {
  if (!self.window || self.window != g_window) return;
  Log("the display's scene disconnected (the display was unplugged, changed its mode, or the app left the "
      "foreground): the picture is back on the phone");
  g_window.hidden = YES;
  g_window = nil;
  self.window = nil;
  g_router.Disconnect(Now());
  Publish();
  ScheduleSettle();
  GiveHost();
}

@end

// The 1-point window for the iOS 27 registration (external_display.h).
@interface NFSExternalDisplayAnchorWindow : UIWindow
@end
@implementation NFSExternalDisplayAnchorWindow
- (BOOL)canBecomeKeyWindow {
  return NO;
}
@end

namespace nfsmw::external_display {

void Start() {
  if (g_started) return;
  UIWindowScene* scene = nfsmw::AppScene();
  if (!scene) return;  // no scene yet: the next call
  g_started = true;
  NSNotificationCenter* center = NSNotificationCenter.defaultCenter;
  [center addObserverForName:UISceneDidActivateNotification object:nil queue:NSOperationQueue.mainQueue
                  usingBlock:^(NSNotification* note) {
                    if (!nfsmw::IsAppScene(note.object)) return;
                    g_router.SetActive(true, Now());
                    ScheduleSettle();
                  }];
  [center addObserverForName:UISceneWillDeactivateNotification object:nil queue:NSOperationQueue.mainQueue
                  usingBlock:^(NSNotification* note) {
                    if (!nfsmw::IsAppScene(note.object)) return;
                    g_router.SetActive(false, Now());
                    ScheduleSettle();
                  }];
  g_router.SetActive(scene.activationState == UISceneActivationStateForegroundActive, Now());

  // iOS 17-26 offer the display's scene from Info.plist; SDL's delegate must
  // leave it alone (tools/ios/patch_ios_sdl_scene.py marks itself).
  Class sdl = NSClassFromString(@"SDLUIKitSceneDelegate");
  const bool sdl_patched = sdl && [sdl respondsToSelector:NSSelectorFromString(@"nfsmwOtherRolesFromInfoPlist")];

#if defined(__IPHONE_27_0)
  if (@available(iOS 27.0, *)) {
    UISceneConfiguration* config =
        [[UISceneConfiguration alloc] initWithName:@"External display"
                                       sessionRole:UIWindowSceneSessionRoleExternalDisplayNonInteractive];
    config.delegateClass = NFSExternalDisplaySceneDelegate.class;
    UIViewController* holder = [UIViewController new];
    holder.view.userInteractionEnabled = NO;
    holder.view.accessibilityElementsHidden = YES;
    holder.view.backgroundColor = UIColor.clearColor;
    // Visible, or iOS offers no scene; 1 point, below every other window,
    // never key. A view controller of the launcher's or the game's window
    // would end the registration at Play, and the display's scene with it.
    g_anchor = [[NFSExternalDisplayAnchorWindow alloc] initWithWindowScene:scene];
    g_anchor.frame = CGRectMake(0, 0, 1, 1);
    g_anchor.windowLevel = UIWindowLevelNormal - 1;
    g_anchor.userInteractionEnabled = NO;
    g_anchor.backgroundColor = UIColor.clearColor;
    g_anchor.rootViewController = holder;
    g_anchor.hidden = NO;
    UISceneAccessoryRegistration* registration =
        [holder registerSceneAccessory:[UISceneAccessory externalNonInteractiveSceneAccessoryWithConfiguration:config]];
    registration.enabled = !g_released;
    g_registration = registration;
    Log("waiting for a display (iOS 27 scene accessory)");
    return;
  }
#endif
  Log("waiting for a display (Info.plist scene manifest; SDL %s)",
      sdl_patched ? "leaves the display's scene to it" : "NOT patched: run tools/ios/patch_ios_sdl_scene.py");
}

bool IsAnchorWindow(UIWindow* window) {
  return [window isKindOfClass:NFSExternalDisplayAnchorWindow.class];
}

void SetPictureHandler(std::function<void(UIView* host)> handler) {
  g_handler = std::move(handler);
  g_given = nil;
  GiveHost();
}

void Release() {
  if (g_released) return;
  g_released = true;
  Log("the game's picture stays on the phone: a display mirrors it");
#if defined(__IPHONE_27_0)
  if (@available(iOS 27.0, *)) {
    if (g_registration) ((UISceneAccessoryRegistration*)g_registration).enabled = NO;
  }
#endif
  if (g_window) {
    g_window.hidden = YES;
    g_window = nil;
    g_router.Disconnect(Now());
    Publish();
    ScheduleSettle();
  }
  GiveHost();
}

bool SizingExternal() {
  return g_sizing_external.load(std::memory_order_acquire);
}

Pixels PicturePixels() {
  return {g_pixels_w.load(), g_pixels_h.load()};
}

void SetMaxWidth(uint32_t max_width) {
  if (g_max_width.exchange(max_width) == max_width) return;
  dispatch_async(dispatch_get_main_queue(), ^{
    UIView* host = g_window.rootViewController.view;
    if (!host) return;
    UpdatePixels(host);
    for (UIView* v in host.subviews) [v setNeedsLayout];
  });
}

uint32_t MaxWidth() {
  return g_max_width.load();
}

bool ConnectedPixels(Pixels* pixels) {
  if (!g_window || g_released) return false;
  UpdatePixels(g_window.rootViewController.view);
  const Pixels p = PicturePixels();
  if (!p.w || !p.h) return false;
  if (pixels) *pixels = p;
  return true;
}

void SetLog(std::function<void(const std::string&)> log) {
  g_log = std::move(log);
}

}  // namespace nfsmw::external_display
