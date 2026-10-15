// NFSMW Recompiled - a Metal GPU frame capture, from a button in the game
//
// To find where a race frame's ~20 ms of GPU time goes (ios/README.md,
// "Settings tried"). Metal can write a capture to a .gputrace document without
// Xcode attached, as long as capturing was enabled before the device was
// created (MTL_CAPTURE_ENABLED=1; LiveContainer's own Info.plist decides the
// MetalCaptureEnabled key, so the environment is what works there).
//
// Native captures start on the renderer queue before encoding and end after
// submitting one frame, including BC uploads and presentation. The emulated
// renderer retains its timed device capture.

#import <Metal/Metal.h>
#import <UIKit/UIKit.h>

#include <rex/logging.h>
#include <rex/cvar.h>
#include <atomic>

#include "gpu_capture.h"
#include "launcher.h"

namespace {
constexpr int64_t kCaptureMs = 50;
std::atomic<bool> native_requested{false};
}

@interface NFSCaptureButton : UIButton
- (void)captureFinished:(NSString*)label;
@end

namespace {
__weak NFSCaptureButton* capture_button;
}

@implementation NFSCaptureButton {
  BOOL _busy;
}

- (instancetype)init {
  if ((self = [super initWithFrame:CGRectZero])) {
    UIButtonConfiguration* c = UIButtonConfiguration.filledButtonConfiguration;
    c.baseBackgroundColor = [UIColor colorWithRed:0.75 green:0.1 blue:0.1 alpha:0.85];
    c.cornerStyle = UIButtonConfigurationCornerStyleCapsule;
    c.contentInsets = NSDirectionalEdgeInsetsMake(4, 10, 4, 10);
    self.configuration = c;
    [self setTitle:@"CAPTURE" forState:UIControlStateNormal];
    self.titleLabel.font = [UIFont boldSystemFontOfSize:12];
    [self addTarget:self action:@selector(capture) forControlEvents:UIControlEventTouchUpInside];
  }
  return self;
}

- (void)setLabel:(NSString*)text {
  UIButtonConfiguration* c = self.configuration;
  c.title = text;
  self.configuration = c;
  [self layoutInSuperview];
}

- (void)layoutInSuperview {
  UIView* parent = self.superview;
  if (!parent) {
    return;
  }
  [self sizeToFit];
  const UIEdgeInsets safe = parent.safeAreaInsets;
  const CGSize s = self.bounds.size;
  self.frame = CGRectMake(parent.bounds.size.width - safe.right - s.width - 8, safe.top + 6,
                          s.width, s.height);
}

- (void)capture {
  if (_busy) {
    return;
  }
  if (rex::cvar::Query<bool>("nfsmw_native_cp") && rex::cvar::Query<bool>("nfsmw_native_present")) {
    _busy = YES;
    [self setLabel:@"NEXT FRAME…"];
    native_requested.store(true, std::memory_order_release);
    return;
  }
  MTLCaptureManager* manager = MTLCaptureManager.sharedCaptureManager;
  if (![manager supportsDestination:MTLCaptureDestinationGPUTraceDocument]) {
    REXLOG_ERROR("[gpu-capture] Metal says it cannot write a capture document: capturing was "
                 "not enabled before the device was created");
    [self setLabel:@"NOT AVAILABLE"];
    return;
  }
  NSString* dir =
      @((nfsmw::launcher::Documents() / "captures").c_str());
  [NSFileManager.defaultManager createDirectoryAtPath:dir
                          withIntermediateDirectories:YES
                                           attributes:nil
                                                error:nil];
  NSDateFormatter* f = [[NSDateFormatter alloc] init];
  f.dateFormat = @"yyyy-MM-dd_HH-mm-ss";
  NSString* path = [dir stringByAppendingPathComponent:
                            [[f stringFromDate:NSDate.date] stringByAppendingString:@".gputrace"]];

  MTLCaptureDescriptor* d = [[MTLCaptureDescriptor alloc] init];
  d.captureObject = MTLCreateSystemDefaultDevice();  // the one MoltenVK uses
  d.destination = MTLCaptureDestinationGPUTraceDocument;
  d.outputURL = [NSURL fileURLWithPath:path];
  NSError* error = nil;
  if (![manager startCaptureWithDescriptor:d error:&error]) {
    REXLOG_ERROR("[gpu-capture] could not start: {}", error.localizedDescription.UTF8String);
    [self setLabel:@"FAILED"];
    return;
  }
  _busy = YES;
  [self setLabel:@"CAPTURING…"];
  REXLOG_INFO("[gpu-capture] started -> {}", path.UTF8String);
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, kCaptureMs * NSEC_PER_MSEC),
                 dispatch_get_main_queue(), ^{
                   [manager stopCapture];
                   REXLOG_INFO("[gpu-capture] stopped after {} ms: {}", kCaptureMs,
                               path.lastPathComponent.UTF8String);
                   [self setLabel:@"SAVED"];
                   dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC),
                                  dispatch_get_main_queue(), ^{
                                    self->_busy = NO;
                                    [self setLabel:@"CAPTURE"];
                                  });
                 });
}

- (void)captureFinished:(NSString*)label {
  [self setLabel:label];
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
    self->_busy = NO;
    [self setLabel:@"CAPTURE"];
  });
}

@end

namespace nfsmw::gpu_capture {

bool BeginNativeFrame(id<MTLCommandQueue> queue) {
  if (!native_requested.exchange(false, std::memory_order_acq_rel)) return false;
  MTLCaptureManager* manager = MTLCaptureManager.sharedCaptureManager;
  auto failed = [] {
    dispatch_async(dispatch_get_main_queue(), ^{ [capture_button captureFinished:@"FAILED"]; });
  };
  if (manager.isCapturing || ![manager supportsDestination:MTLCaptureDestinationGPUTraceDocument]) {
    REXLOG_ERROR("[gpu-capture] native capture unavailable (another capture active, or capture layer disabled)");
    failed();
    return false;
  }
  NSString* dir = @((nfsmw::launcher::Documents() / "captures").c_str());
  NSError* error = nil;
  if (![NSFileManager.defaultManager createDirectoryAtPath:dir withIntermediateDirectories:YES
                                              attributes:nil error:&error]) {
    REXLOG_ERROR("[gpu-capture] cannot create capture directory: {}", error.localizedDescription.UTF8String);
    failed();
    return false;
  }
  NSDateFormatter* formatter = [[NSDateFormatter alloc] init];
  formatter.dateFormat = @"yyyy-MM-dd_HH-mm-ss-SSS";
  NSString* path = [dir stringByAppendingPathComponent:
      [[formatter stringFromDate:NSDate.date] stringByAppendingString:@".gputrace"]];
  MTLCaptureDescriptor* descriptor = [[MTLCaptureDescriptor alloc] init];
  descriptor.captureObject = queue;
  descriptor.destination = MTLCaptureDestinationGPUTraceDocument;
  descriptor.outputURL = [NSURL fileURLWithPath:path];
  if (![manager startCaptureWithDescriptor:descriptor error:&error]) {
    REXLOG_ERROR("[gpu-capture] native capture could not start: {}", error.localizedDescription.UTF8String);
    failed();
    return false;
  }
  REXLOG_INFO("[gpu-capture] native frame started -> {}", path.UTF8String);
  dispatch_async(dispatch_get_main_queue(), ^{ [capture_button setLabel:@"CAPTURING…"]; });
  return true;
}

void EndNativeFrame() {
  [MTLCaptureManager.sharedCaptureManager stopCapture];
  REXLOG_INFO("[gpu-capture] native frame capture stopped after command-buffer submission");
  dispatch_async(dispatch_get_main_queue(), ^{ [capture_button captureFinished:@"SAVED"]; });
}

void InstallButton() {
  static bool installed = false;
  if (installed) {
    return;
  }
  UIWindow* window = nil;
  for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
    if ([scene isKindOfClass:UIWindowScene.class] &&
        ((UIWindowScene*)scene).screen == UIScreen.mainScreen) {
      for (UIWindow* w in ((UIWindowScene*)scene).windows) {
        if (w.isKeyWindow || !window) {
          window = w;
        }
      }
    }
  }
  if (!window) {
    return;
  }
  NFSCaptureButton* button = [[NFSCaptureButton alloc] init];
  capture_button = button;
  [window addSubview:button];
  [button layoutInSuperview];
  installed = true;
  REXLOG_INFO("[gpu-capture] button on screen (Metal capture to documents: {})",
              [MTLCaptureManager.sharedCaptureManager
                  supportsDestination:MTLCaptureDestinationGPUTraceDocument]
                  ? "available"
                  : "NOT available");
}

}  // namespace nfsmw::gpu_capture
