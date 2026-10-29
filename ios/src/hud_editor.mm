// NFSMW Recompiled - the Customize HUD editor
//
// Stefan, Oct 29: the HUD's size/position rows replaced by one screen where
// each element is moved by hand, two master sliders (HUD size, safe zone),
// tabs for race/free roam and pursuit (each has elements the other lacks),
// no element over another, and a size per element. Elements are outlines
// for now (pictures of them later).
//
// Units: HUD units, as game_scene_size.cpp uses them (480 down the screen at
// full size, from the middle of the screen, y down). On the iPad (4:3) the
// game takes its SD layout: the HUD fills the height, its sides at 221. On
// wider screens its HD layout: the title-safe 0.92 kept (the screen is
// 480 / 0.92 units tall), the sides 120 further out, and on 19.5:9 the wide
// scene's extra (ExtraHudOffset). Each element is drawn where
// game_scene_size.cpp puts it: with its corner g (the outer corner it keeps
// at the safe zone k), the HUD size s, its own size e and the offset u from
// the layout, a point p of it is drawn at k * g + u + s * e * (p - g).
// Boxes: each element's extent at full size, read from the 100% iPad
// screenshots of Oct 29 (IPA141, IMG_0334/0335: 3.125 points per unit).

#import "hud_editor.h"

#include <algorithm>
#include <cmath>

namespace {

struct ElementBox {
  NSString* key;   // nfsmw_hud_layout's name
  NSString* title;
  int tabs;        // 1 race/free roam, 2 pursuit
  float side;      // -1 left, 1 right, 0 middle
  float corner_y;  // the corner's y (game_scene_size.cpp's kCorners)
  float dx;        // the middle's x: side * (sides + dx), or dx in the middle
  float y;         // the middle's y
  float w, h;
  bool sized;      // its own size can change
};

// The minimap's and the mirror's pictures are drawn apart from their pieces:
// their own size stays 1 (game_scene_size.cpp's ReadLayout).
const ElementBox kBoxes[] = {
    {@"minimap", @"Minimap", 3, -1, 215, 1, 137, 140, 140, false},
    {@"speedometer", @"Speedometer", 3, 1, 215, 1, 137, 145, 140, true},
    {@"race_info", @"Race / pursuit info", 3, 1, -213, -11, -144, 176, 108, true},
    {@"mirror", @"Mirror", 3, 0, -220, 0, -176, 210, 76, false},
    {@"infractions", @"Infractions", 2, -1, -213, 1, -152, 140, 100, true},
    {@"pursuit_bar", @"Busted / evade bar", 2, 0, 215, 0, 166, 220, 64, true},
    {@"pursuit_points", @"Pursuit points", 2, 1, 215, 0, 41, 130, 30, true},
};
constexpr int kCount = int(sizeof(kBoxes) / sizeof(kBoxes[0]));
constexpr float kHalfWidth = 76.0f;  // game_scene_size.cpp's: corners this far past the sides

struct Placed {
  float x = 0, y = 0, size = 1;
};

}  // namespace

@interface NFSHudEditor : UIViewController
- (instancetype)initWithSettings:(NSMutableDictionary<NSString*, NSString*>*)settings changed:(void (^)(void))changed;
@end

@implementation NFSHudEditor {
  NSMutableDictionary<NSString*, NSString*>* _settings;
  void (^_changed)(void);
  Placed _placed[kCount];
  UIView* _canvas;
  UIView* _boxes[kCount];
  UISegmentedControl* _tab;
  UISlider* _size;
  UISlider* _safe;
  UILabel* _sizeLabel;
  UILabel* _safeLabel;
  int _selected;
  CGPoint _dragStart;  // the element's x, y when its drag began
}

- (instancetype)initWithSettings:(NSMutableDictionary<NSString*, NSString*>*)settings changed:(void (^)(void))changed {
  if ((self = [super init])) {
    _settings = settings;
    _changed = changed;
    _selected = -1;
    [self readLayout];
  }
  return self;
}

- (UIInterfaceOrientationMask)supportedInterfaceOrientations {
  return UIInterfaceOrientationMaskLandscape;
}

- (BOOL)prefersStatusBarHidden {
  return YES;
}

// ---------------------------------------------------------------------------
//  The settings
// ---------------------------------------------------------------------------

- (float)setting:(NSString*)key fallback:(float)fallback {
  NSString* v = _settings[key];
  return v.length ? v.floatValue : fallback;
}

- (float)hudSize {
  return std::clamp([self setting:@"hud_scale" fallback:1.0f], 0.5f, 1.5f);
}

- (float)safeZone {
  return std::clamp([self setting:@"hud_safe_zone" fallback:1.0f], 0.5f, 1.5f);
}

- (void)readLayout {
  for (int i = 0; i < kCount; ++i) _placed[i] = Placed();
  for (NSString* item in [_settings[@"hud_layout"] ?: @"" componentsSeparatedByString:@";"]) {
    NSArray<NSString*>* kv = [item componentsSeparatedByString:@":"];
    if (kv.count != 2) continue;
    NSArray<NSString*>* v = [kv[1] componentsSeparatedByString:@","];
    for (int i = 0; i < kCount; ++i) {
      if (![kBoxes[i].key isEqualToString:kv[0]] || v.count < 2) continue;
      _placed[i].x = v[0].floatValue;
      _placed[i].y = v[1].floatValue;
      _placed[i].size = v.count > 2 && kBoxes[i].sized ? std::clamp(v[2].floatValue, 0.5f, 2.0f) : 1.0f;
    }
  }
}

- (void)save {
  NSMutableArray<NSString*>* items = [NSMutableArray array];
  for (int i = 0; i < kCount; ++i) {
    const Placed& p = _placed[i];
    if (std::abs(p.x) < 0.5f && std::abs(p.y) < 0.5f && std::abs(p.size - 1.0f) < 0.005f) continue;
    [items addObject:[NSString stringWithFormat:@"%@:%.0f,%.0f,%.2f", kBoxes[i].key, p.x, p.y, p.size]];
  }
  _settings[@"hud_layout"] = [items componentsJoinedByString:@";"];
  if (_changed) _changed();
}

// ---------------------------------------------------------------------------
//  Geometry
// ---------------------------------------------------------------------------

- (CGSize)screen {
  return _canvas.bounds.size;
}

// HD: the game's 16:9-and-wider layout.
- (bool)hd {
  const CGSize s = [self screen];
  return s.height > 0 && s.width / s.height > 1.5;
}

- (float)unitsTall {
  return [self hd] ? 480.0f / 0.92f : 480.0f;
}

- (float)pointsPerUnit {
  return float([self screen].height) / [self unitsTall];
}

// Where the sides are: 221 at 4:3, 120 further in HD, plus the wide scene's
// extra (game_scene_size.cpp's ExtraHudOffset, for the width the launcher
// picks: 720 times the aspect, at most 1600).
- (float)sides {
  if (![self hd]) return 221.0f;
  const CGSize s = [self screen];
  const float aspect = float(s.width / s.height);
  float extra = 0;
  if (aspect > 16.0f / 9.0f + 0.05f) {
    const float width = std::min(1600.0f, 720.0f * aspect);
    extra = 120.0f * (width / 720.0f - 16.0f / 9.0f) / (16.0f / 9.0f - 4.0f / 3.0f);
  }
  return 221.0f + 120.0f + extra;
}

// An element's box in HUD units (middle, size) for a placement.
- (CGRect)unitsRect:(int)i placed:(const Placed&)p {
  const ElementBox& b = kBoxes[i];
  const float g = [self sides];
  const float corner_x = b.side * (g + kHalfWidth);
  const float mid_x = b.side != 0 ? b.side * (g + b.dx) : b.dx;
  const float k = [self safeZone], s = [self hudSize] * p.size;
  const float x = k * corner_x + p.x + s * (mid_x - corner_x);
  const float y = k * b.corner_y + p.y + s * (b.y - b.corner_y);
  return CGRectMake(x - s * b.w / 2, y - s * b.h / 2, s * b.w, s * b.h);
}

- (CGRect)pointsRect:(int)i placed:(const Placed&)p {
  const CGRect u = [self unitsRect:i placed:p];
  const CGFloat ppu = [self pointsPerUnit];
  const CGSize s = [self screen];
  return CGRectMake(s.width / 2 + u.origin.x * ppu, s.height / 2 + u.origin.y * ppu, u.size.width * ppu,
                    u.size.height * ppu);
}

- (bool)shown:(int)i {
  return (kBoxes[i].tabs & (_tab.selectedSegmentIndex == 0 ? 1 : 2)) != 0;
}

// Whether element i at p stays on the screen and off the others shown (one
// it already overlaps, at the sliders' doing, is not held against it).
- (bool)fits:(int)i placed:(const Placed&)p {
  const CGRect r = [self pointsRect:i placed:p];
  if (!CGRectContainsRect(CGRectInset(_canvas.bounds, -1, -1), r)) return false;
  const CGRect now = [self pointsRect:i placed:_placed[i]];
  for (int j = 0; j < kCount; ++j) {
    if (j == i || ![self shown:j]) continue;
    const CGRect other = [self pointsRect:j placed:_placed[j]];
    if (CGRectIntersectsRect(r, other) && !CGRectIntersectsRect(now, other)) return false;
  }
  return true;
}

// ---------------------------------------------------------------------------
//  The screen
// ---------------------------------------------------------------------------

- (UIButton*)button:(NSString*)title action:(SEL)action {
  UIButtonConfiguration* c = UIButtonConfiguration.filledButtonConfiguration;
  c.title = title;
  c.cornerStyle = UIButtonConfigurationCornerStyleCapsule;
  c.contentInsets = NSDirectionalEdgeInsetsMake(6, 12, 6, 12);
  UIButton* b = [UIButton buttonWithConfiguration:c primaryAction:nil];
  [b addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];
  return b;
}

- (UIStackView*)slider:(UISlider* __strong*)slider label:(UILabel* __strong*)label min:(float)min max:(float)max
                action:(SEL)action {
  *label = [[UILabel alloc] init];
  (*label).textColor = UIColor.whiteColor;
  (*label).font = [UIFont monospacedDigitSystemFontOfSize:13 weight:UIFontWeightSemibold];
  *slider = [[UISlider alloc] init];
  (*slider).minimumValue = min;
  (*slider).maximumValue = max;
  [*slider addTarget:self action:action forControlEvents:UIControlEventValueChanged];
  [(*slider).widthAnchor constraintEqualToConstant:120].active = YES;
  UIStackView* row = [[UIStackView alloc] initWithArrangedSubviews:@[ *label, *slider ]];
  row.spacing = 8;
  row.alignment = UIStackViewAlignmentCenter;
  return row;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.view.backgroundColor = UIColor.blackColor;
  _canvas = [[UIView alloc] initWithFrame:self.view.bounds];
  _canvas.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
  _canvas.backgroundColor = [UIColor colorWithRed:0.12 green:0.13 blue:0.16 alpha:1];
  [_canvas addGestureRecognizer:[[UITapGestureRecognizer alloc] initWithTarget:self action:@selector(tapEmpty)]];
  [self.view addSubview:_canvas];

  for (int i = 0; i < kCount; ++i) {
    UIView* box = [[UIView alloc] init];
    box.layer.borderWidth = 2;
    box.layer.cornerRadius = 8;
    UILabel* label = [[UILabel alloc] init];
    label.text = kBoxes[i].title;
    label.textColor = UIColor.whiteColor;
    label.font = [UIFont systemFontOfSize:12 weight:UIFontWeightSemibold];
    label.textAlignment = NSTextAlignmentCenter;
    label.numberOfLines = 2;
    label.adjustsFontSizeToFitWidth = YES;
    label.minimumScaleFactor = 0.6;
    label.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    [box addSubview:label];
    box.tag = i;
    [box addGestureRecognizer:[[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(drag:)]];
    [box addGestureRecognizer:[[UITapGestureRecognizer alloc] initWithTarget:self action:@selector(tapBox:)]];
    [_canvas addSubview:box];
    _boxes[i] = box;
  }

  _tab = [[UISegmentedControl alloc] initWithItems:@[ @"Race / Free roam", @"Pursuit" ]];
  _tab.selectedSegmentIndex = 0;
  [_tab addTarget:self action:@selector(tabChanged) forControlEvents:UIControlEventValueChanged];
  UIStackView* top = [[UIStackView alloc] initWithArrangedSubviews:@[
    _tab, [self button:@"Smaller" action:@selector(smaller)], [self button:@"Bigger" action:@selector(bigger)],
    [self button:@"Reset" action:@selector(confirmReset)], [self button:@"Done" action:@selector(done)]
  ]];
  top.spacing = 10;
  top.alignment = UIStackViewAlignmentCenter;
  top.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:top];

  UIStackView* bottom = [[UIStackView alloc] initWithArrangedSubviews:@[
    [self slider:&_size label:&_sizeLabel min:0.7f max:1.3f action:@selector(sizeChanged)],
    [self slider:&_safe label:&_safeLabel min:0.8f max:1.1f action:@selector(safeChanged)]
  ]];
  bottom.spacing = 24;
  bottom.alignment = UIStackViewAlignmentCenter;
  bottom.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:bottom];
  _size.value = [self hudSize];
  _safe.value = [self safeZone];

  UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    // In the middle of the screen, where the HUD has nothing.
    [top.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
    [top.centerYAnchor constraintEqualToAnchor:safe.centerYAnchor constant:-22],
    [bottom.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
    [bottom.topAnchor constraintEqualToAnchor:top.bottomAnchor constant:10],
  ]];
  [self updateLabels];
}

- (void)viewDidLayoutSubviews {
  [super viewDidLayoutSubviews];
  [self layoutBoxes];
}

- (void)updateLabels {
  _sizeLabel.text = [NSString stringWithFormat:@"HUD size %d%%", int(std::lround([self hudSize] * 100))];
  _safeLabel.text = [NSString stringWithFormat:@"Safe zone %d%%", int(std::lround([self safeZone] * 100))];
}

- (void)layoutBoxes {
  for (int i = 0; i < kCount; ++i) {
    UIView* box = _boxes[i];
    box.hidden = ![self shown:i];
    box.frame = [self pointsRect:i placed:_placed[i]];
    const bool selected = i == _selected;
    box.layer.borderColor = (selected ? UIColor.systemOrangeColor : [UIColor colorWithWhite:1 alpha:0.7]).CGColor;
    box.backgroundColor = selected ? [UIColor colorWithRed:1 green:0.6 blue:0.1 alpha:0.25]
                                   : [UIColor colorWithWhite:1 alpha:0.08];
    UILabel* label = box.subviews.firstObject;
    label.frame = CGRectInset(box.bounds, 4, 2);
    label.text = kBoxes[i].sized && std::abs(_placed[i].size - 1.0f) > 0.005f
                     ? [NSString stringWithFormat:@"%@ %d%%", kBoxes[i].title, int(std::lround(_placed[i].size * 100))]
                     : kBoxes[i].title;
  }
}

// ---------------------------------------------------------------------------
//  Editing
// ---------------------------------------------------------------------------

- (void)tabChanged {
  if (_selected >= 0 && ![self shown:_selected]) _selected = -1;
  [self layoutBoxes];
}

- (void)tapEmpty {
  _selected = -1;
  [self layoutBoxes];
}

- (void)tapBox:(UITapGestureRecognizer*)tap {
  _selected = int(tap.view.tag);
  [self layoutBoxes];
}

- (void)drag:(UIPanGestureRecognizer*)pan {
  const int i = int(pan.view.tag);
  if (pan.state == UIGestureRecognizerStateBegan) {
    _selected = i;
    _dragStart = CGPointMake(_placed[i].x, _placed[i].y);
  }
  const CGPoint t = [pan translationInView:_canvas];
  const float ppu = [self pointsPerUnit];
  Placed want = _placed[i];
  want.x = float(_dragStart.x) + float(t.x) / ppu;
  want.y = float(_dragStart.y) + float(t.y) / ppu;
  // Against an edge or another element: slide along it (x and y on their own).
  if ([self fits:i placed:want]) {
    _placed[i] = want;
  } else {
    Placed only_x = _placed[i], only_y = _placed[i];
    only_x.x = want.x;
    only_y.y = want.y;
    if ([self fits:i placed:only_x]) _placed[i] = only_x;
    if ([self fits:i placed:only_y]) _placed[i].y = only_y.y;
  }
  [self layoutBoxes];
  if (pan.state == UIGestureRecognizerStateEnded || pan.state == UIGestureRecognizerStateCancelled) [self save];
}

- (void)resize:(float)factor {
  if (_selected < 0 || !kBoxes[_selected].sized) return;
  Placed want = _placed[_selected];
  want.size = std::clamp(want.size * factor, 0.5f, 2.0f);
  if (![self fits:_selected placed:want]) return;
  _placed[_selected] = want;
  [self layoutBoxes];
  [self save];
}

- (void)smaller {
  [self resize:1.0f / 1.1f];
}

- (void)bigger {
  [self resize:1.1f];
}

- (void)sizeChanged {
  const float v = std::round(_size.value * 20.0f) / 20.0f;  // 5% steps
  _settings[@"hud_scale"] = [NSString stringWithFormat:@"%.2f", v];
  [self updateLabels];
  [self layoutBoxes];
  if (_changed) _changed();
}

- (void)safeChanged {
  const float v = std::round(_safe.value * 50.0f) / 50.0f;  // 2% steps
  _settings[@"hud_safe_zone"] = [NSString stringWithFormat:@"%.2f", v];
  [self updateLabels];
  [self layoutBoxes];
  if (_changed) _changed();
}

- (void)confirmReset {
  UIAlertController* alert =
      [UIAlertController alertControllerWithTitle:@"Reset the HUD?"
                                          message:@"Every element goes back to the game's place and size, and "
                                                  @"the HUD size and safe zone to 100%."
                                   preferredStyle:UIAlertControllerStyleAlert];
  [alert addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  [alert addAction:[UIAlertAction actionWithTitle:@"Reset"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) {
                                            self->_settings[@"hud_scale"] = @"1.00";
                                            self->_settings[@"hud_safe_zone"] = @"1.00";
                                            self->_settings[@"hud_layout"] = @"";
                                            [self readLayout];
                                            self->_size.value = 1.0f;
                                            self->_safe.value = 1.0f;
                                            self->_selected = -1;
                                            [self updateLabels];
                                            [self layoutBoxes];
                                            if (self->_changed) self->_changed();
                                          }]];
  [self presentViewController:alert animated:YES completion:nil];
}

- (void)done {
  [self dismissViewControllerAnimated:YES completion:nil];
}

@end

namespace nfsmw::hud {

UIViewController* MakeEditor(NSMutableDictionary<NSString*, NSString*>* settings, void (^changed)(void)) {
  NFSHudEditor* editor = [[NFSHudEditor alloc] initWithSettings:settings changed:changed];
  editor.modalPresentationStyle = UIModalPresentationFullScreen;
  return editor;
}

}  // namespace nfsmw::hud
