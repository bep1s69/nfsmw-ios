// NFSMW Recompiled - the pre-launch screen on iOS
//
// The iOS counterpart of Android's SetupActivity + Ajustes
// (android/app/src/main/java/io/github/nfsmwrecomp/): the same sections, the
// same options and texts, for what exists on iOS. Not here, and why:
//   - GPU driver import, GPU turbo, thread affinity: Android only. iOS gets
//     its own two performance switches instead (thread QoS, async submits).
//   - The native engine's options (render resolution, fps limit, shadows,
//     reflections, filters, AAudio): that engine is not part of the iOS port.
//   - App language: the iOS app is English only.
//   - Tilt steering and the touch layout editor: tilt only acts while driving,
//     and only the native engine can tell when that is (on Android's Xenos
//     engine it never turns on); both come later.
//
// It runs before the game: main() calls Run(), which puts a UIKit window up
// and spins the main run loop until Play is tapped (the way SDL shows its own
// message boxes on iOS), then takes the window down. The game's SDL window is
// created after that.
//
// Settings live in Documents/settings.json (string values), saved on every
// change, so they can be read and edited from the Files app too.

#include "app_scene.h"
#import <UIKit/UIKit.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <functional>
#include <regex>
#include <system_error>
#include <unordered_map>

#include "launcher.h"
#include "settings_catalog.h"
#include "settings_ui.h"
#import <GameController/GameController.h>
#include "multiplayer/lan_session.h"
#include "multiplayer/lan_setup.h"
#include "multiplayer/servidor_ea.h"
#include "multiplayer/pc_gateway.h"
#include "multiplayer/red_lan.h"
#include "hud_editor.h"
#include "touch_controls.h"
#include "save_manager.h"
#include <dlfcn.h>
#include <mach-o/loader.h>

namespace fs = std::filesystem;

namespace {

using namespace nfsmw::catalog;


NSString* FileSize(const fs::path& p) {
  std::error_code ec;
  const auto bytes = fs::file_size(p, ec);
  return ec ? @"?" : [NSByteCountFormatter stringFromByteCount:(long long)bytes
                                                    countStyle:NSByteCountFormatterCountStyleFile];
}

// ---------------------------------------------------------------------------
//  Achievements
// ---------------------------------------------------------------------------
// The list comes from the game itself (achievements_export.cpp writes
// Documents/achievements/list.json and icons/ when the game starts); what is
// unlocked, from the SDK's own file, Documents/data/achievements/<title>.toml:
//
//   [unlocked.<id>]
//   filetime = <Windows FILETIME>
struct Achievement {
  uint32_t id = 0;
  NSString* name = @"";
  NSString* description = @"";
  NSString* locked_description = @"";
  uint32_t gamerscore = 0;
  NSString* icon = nil;  // full path, or nil
  bool unlocked = false;
  uint64_t filetime = 0;
};

struct Achievements {
  bool loaded = false;  // false until the game has run once
  std::vector<Achievement> list;
  size_t unlocked = 0;
  uint32_t gamerscore = 0, gamerscore_total = 0;
};

Achievements LoadAchievements(const fs::path& docs) {
  Achievements out;
  const fs::path dir = docs / "achievements";
  NSData* data = [NSData dataWithContentsOfFile:@((dir / "list.json").c_str())];
  NSDictionary* json = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil]
                            : nil;
  NSArray* items = [json isKindOfClass:NSDictionary.class] ? json[@"achievements"] : nil;
  if (![items isKindOfClass:NSArray.class]) {
    return out;
  }
  out.loaded = true;

  // What is unlocked: "[unlocked.<id>]" then "filetime = <n>".
  std::unordered_map<uint32_t, uint64_t> unlocked;
  NSString* title = [json[@"title_id"] isKindOfClass:NSString.class] ? json[@"title_id"] : @"";
  NSString* toml = [NSString
      stringWithContentsOfFile:@((docs / "data" / "achievements" / (std::string(title.UTF8String) + ".toml")).c_str())
                      encoding:NSUTF8StringEncoding
                         error:nil];
  uint32_t current = 0;
  bool in_entry = false;
  for (NSString* raw in [toml componentsSeparatedByCharactersInSet:NSCharacterSet.newlineCharacterSet]) {
    NSString* line = [raw stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
    if ([line hasPrefix:@"[unlocked."] && [line hasSuffix:@"]"]) {
      current = uint32_t([[line substringWithRange:NSMakeRange(10, line.length - 11)] longLongValue]);
      in_entry = true;
      unlocked[current] = 0;
    } else if (in_entry && [line hasPrefix:@"filetime"]) {
      NSRange eq = [line rangeOfString:@"="];
      if (eq.location != NSNotFound) {
        unlocked[current] = strtoull([line substringFromIndex:eq.location + 1].UTF8String, nullptr, 10);
      }
    }
  }

  for (NSDictionary* item in items) {
    if (![item isKindOfClass:NSDictionary.class]) {
      continue;
    }
    Achievement a;
    a.id = [item[@"id"] unsignedIntValue];
    a.name = item[@"name"] ?: @"";
    a.description = item[@"description"] ?: @"";
    a.locked_description = item[@"locked_description"] ?: @"";
    a.gamerscore = [item[@"gamerscore"] unsignedIntValue];
    NSString* icon = item[@"icon"];
    if (icon.length) {
      a.icon = @((dir / icon.UTF8String).c_str());
    }
    auto u = unlocked.find(a.id);
    a.unlocked = u != unlocked.end();
    a.filetime = a.unlocked ? u->second : 0;
    out.unlocked += a.unlocked;
    out.gamerscore += a.unlocked ? a.gamerscore : 0;
    out.gamerscore_total += a.gamerscore;
    out.list.push_back(a);
  }
  return out;
}

NSString* AchievementSummary(const Achievements& a) {
  return [NSString stringWithFormat:@"%zu of %zu unlocked · %u of %u G", a.unlocked,
                                    a.list.size(), a.gamerscore, a.gamerscore_total];
}

}  // namespace

// ---------------------------------------------------------------------------
//  The achievement list
// ---------------------------------------------------------------------------
@interface NFSAchievementsController : UITableViewController
- (instancetype)initWithAchievements:(Achievements)achievements;
@end

@implementation NFSAchievementsController {
  Achievements _a;
  NSCache<NSString*, UIImage*>* _icons;
}

- (instancetype)initWithAchievements:(Achievements)achievements {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _a = std::move(achievements);
    _icons = [[NSCache alloc] init];
    self.title = @"Achievements";
  }
  return self;
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  return NSInteger(_a.list.size());
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  return AchievementSummary(_a);
}

- (UIImage*)iconFor:(const Achievement&)a {
  if (!a.icon) {
    return [UIImage systemImageNamed:@"trophy"];
  }
  UIImage* image = [_icons objectForKey:a.icon];
  if (!image) {
    image = [UIImage imageWithContentsOfFile:a.icon] ?: [UIImage systemImageNamed:@"trophy"];
    [_icons setObject:image forKey:a.icon];
  }
  return image;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  const Achievement& a = _a.list[size_t(ip.row)];
  UITableViewCell* cell = [tableView dequeueReusableCellWithIdentifier:@"a"]
                              ?: [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault
                                                        reuseIdentifier:@"a"];
  cell.selectionStyle = UITableViewCellSelectionStyleNone;
  UIListContentConfiguration* c = UIListContentConfiguration.subtitleCellConfiguration;
  c.text = a.name;
  c.textProperties.font = [UIFont preferredFontForTextStyle:UIFontTextStyleHeadline];
  NSString* text = a.unlocked || a.locked_description.length == 0 ? a.description
                                                                  : a.locked_description;
  NSString* status = @"Locked";
  if (a.unlocked) {
    status = @"Unlocked";
    if (a.filetime > 116444736000000000ULL) {
      NSDate* when = [NSDate dateWithTimeIntervalSince1970:double(a.filetime - 116444736000000000ULL) / 1e7];
      status = [@"Unlocked " stringByAppendingString:
                                 [NSDateFormatter localizedStringFromDate:when
                                                                dateStyle:NSDateFormatterMediumStyle
                                                                timeStyle:NSDateFormatterShortStyle]];
    }
  }
  c.secondaryText = [NSString stringWithFormat:@"%@\n%u G · %@", text, a.gamerscore, status];
  c.secondaryTextProperties.color = UIColor.secondaryLabelColor;
  c.secondaryTextProperties.numberOfLines = 0;
  c.textToSecondaryTextVerticalPadding = 4;
  c.image = [self iconFor:a];
  c.imageProperties.maximumSize = CGSizeMake(56, 56);
  c.imageProperties.reservedLayoutSize = CGSizeMake(56, 56);
  c.imageProperties.cornerRadius = 6;
  c.imageToTextPadding = 14;
  cell.contentConfiguration = c;
  // Locked: dimmed, as on the console.
  cell.contentView.alpha = a.unlocked ? 1.0 : 0.45;
  cell.accessoryType = a.unlocked ? UITableViewCellAccessoryCheckmark : UITableViewCellAccessoryNone;
  return cell;
}

@end

// ---------------------------------------------------------------------------
//  The screen
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
//  Keyboard controls: the editor
// ---------------------------------------------------------------------------
// "Press a key": takes the next key from a hardware keyboard (UIPress), shown
// as a sheet; Cancel (or a tap outside) leaves the binding as it was.
@interface NFSKeyCaptureController : UIViewController
- (instancetype)initWithPrompt:(NSString*)prompt done:(void (^)(NSString* key))done;
@end

// Extra arguments, edited full screen (many test options did not fit the
// row's one-line field): one per line, monospaced, no autocorrection or smart
// punctuation; saved as typed, on every change.
@interface NFSArgumentsEditorController : UIViewController <UITextViewDelegate>
- (instancetype)initWithText:(NSString*)text changed:(void (^)(NSString*))changed;
@end

@implementation NFSArgumentsEditorController {
  NSString* _text;
  void (^_changed)(NSString*);
  UITextView* _view;
}

- (instancetype)initWithText:(NSString*)text changed:(void (^)(NSString*))changed {
  if ((self = [super initWithNibName:nil bundle:nil])) {
    // Written on one line before (separated by spaces): shown one per line.
    NSArray* words = [[text componentsSeparatedByCharactersInSet:NSCharacterSet.whitespaceCharacterSet]
        filteredArrayUsingPredicate:[NSPredicate predicateWithFormat:@"length > 0"]];
    _text = [text containsString:@"\n"] ? text : [words componentsJoinedByString:@"\n"];
    _changed = changed;
    self.title = @"Extra arguments";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.view.backgroundColor = UIColor.systemBackgroundColor;
  _view = [[UITextView alloc] init];
  _view.translatesAutoresizingMaskIntoConstraints = NO;
  _view.font = [UIFont monospacedSystemFontOfSize:15 weight:UIFontWeightRegular];
  _view.text = _text;
  _view.autocorrectionType = UITextAutocorrectionTypeNo;
  _view.autocapitalizationType = UITextAutocapitalizationTypeNone;
  _view.spellCheckingType = UITextSpellCheckingTypeNo;
  _view.smartDashesType = UITextSmartDashesTypeNo;
  _view.smartQuotesType = UITextSmartQuotesTypeNo;
  _view.smartInsertDeleteType = UITextSmartInsertDeleteTypeNo;
  _view.alwaysBounceVertical = YES;
  _view.keyboardDismissMode = UIScrollViewKeyboardDismissModeInteractive;
  _view.textContainerInset = UIEdgeInsetsMake(12, 8, 12, 8);
  _view.delegate = self;
  [self.view addSubview:_view];
  UILabel* hint = [[UILabel alloc] init];
  hint.translatesAutoresizingMaskIntoConstraints = NO;
  hint.text = @"One option per line (or separated by spaces), e.g. --nfsmw_hud_watch=true. "
              @"They win over the settings and Documents/extra_args.txt.";
  hint.font = [UIFont preferredFontForTextStyle:UIFontTextStyleFootnote];
  hint.textColor = UIColor.secondaryLabelColor;
  hint.numberOfLines = 0;
  [self.view addSubview:hint];
  UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    [hint.topAnchor constraintEqualToAnchor:safe.topAnchor constant:8],
    [hint.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:16],
    [hint.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-16],
    [_view.topAnchor constraintEqualToAnchor:hint.bottomAnchor constant:4],
    [_view.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor],
    [_view.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor],
    [_view.bottomAnchor constraintEqualToAnchor:self.view.keyboardLayoutGuide.topAnchor],
  ]];
  self.navigationItem.rightBarButtonItem =
      [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone
                                                   primaryAction:[UIAction actionWithHandler:^(UIAction*) {
                                                     [self->_view resignFirstResponder];
                                                     [self.navigationController popViewControllerAnimated:YES];
                                                   }]];
  self.navigationItem.leftItemsSupplementBackButton = YES;
  self.navigationItem.leftBarButtonItem =
      [[UIBarButtonItem alloc] initWithPrimaryAction:[UIAction actionWithTitle:@"Clear"
                                                                         image:nil
                                                                    identifier:nil
                                                                       handler:^(UIAction*) {
                                                                         self->_view.text = @"";
                                                                         [self textViewDidChange:self->_view];
                                                                       }]];
}

- (void)viewDidAppear:(BOOL)animated {
  [super viewDidAppear:animated];
  if (!_view.text.length) [_view becomeFirstResponder];
}

- (void)textViewDidChange:(UITextView*)view {
  _changed(view.text);
}
@end

@implementation NFSKeyCaptureController {
  NSString* _prompt;
  void (^_done)(NSString*);
  UILabel* _hint;
}

- (instancetype)initWithPrompt:(NSString*)prompt done:(void (^)(NSString*))done {
  if ((self = [super initWithNibName:nil bundle:nil])) {
    _prompt = prompt;
    _done = done;
    self.modalPresentationStyle = UIModalPresentationFormSheet;
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.view.backgroundColor = UIColor.systemBackgroundColor;
  UILabel* title = [[UILabel alloc] init];
  title.text = _prompt;
  title.font = [UIFont preferredFontForTextStyle:UIFontTextStyleTitle2];
  title.numberOfLines = 0;
  title.textAlignment = NSTextAlignmentCenter;
  _hint = [[UILabel alloc] init];
  _hint.text = @"Press a key on the keyboard.";
  _hint.textColor = UIColor.secondaryLabelColor;
  _hint.numberOfLines = 0;
  _hint.textAlignment = NSTextAlignmentCenter;
  UIButton* cancel = [UIButton buttonWithType:UIButtonTypeSystem];
  [cancel setTitle:@"Cancel" forState:UIControlStateNormal];
  [cancel addAction:[UIAction actionWithHandler:^(UIAction*) {
            [self dismissViewControllerAnimated:YES completion:nil];
          }]
      forControlEvents:UIControlEventTouchUpInside];
  UIStackView* stack = [[UIStackView alloc] initWithArrangedSubviews:@[ title, _hint, cancel ]];
  stack.axis = UILayoutConstraintAxisVertical;
  stack.spacing = 16;
  stack.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:stack];
  [NSLayoutConstraint activateConstraints:@[
    [stack.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
    [stack.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor],
    [stack.leadingAnchor constraintGreaterThanOrEqualToAnchor:self.view.leadingAnchor constant:24],
  ]];
}

- (BOOL)canBecomeFirstResponder {
  return YES;
}

- (void)viewDidAppear:(BOOL)animated {
  [super viewDidAppear:animated];
  [self becomeFirstResponder];
}

- (void)pressesBegan:(NSSet<UIPress*>*)presses withEvent:(UIPressesEvent*)event {
  for (UIPress* press in presses) {
    if (!press.key) continue;
    NSString* name = KeyName(press.key.keyCode);
    if (!name) {
      _hint.text = @"That key cannot be used. Press another one.";
      continue;
    }
    void (^done)(NSString*) = _done;
    [self dismissViewControllerAnimated:YES completion:^{
      done(name);
    }];
    return;
  }
  [super pressesBegan:presses withEvent:event];
}

@end

// The list of actions and their keys. Tapping one: replace its key, add a
// second one, clear it or put the default back.
@interface NFSKeyBindsController : UITableViewController
- (instancetype)initWithSettings:(NSMutableDictionary<NSString*, NSString*>*)settings
                            save:(void (^)(void))save;
@end

@implementation NFSKeyBindsController {
  NSMutableDictionary<NSString*, NSString*>* _settings;
  void (^_save)(void);
}

- (instancetype)initWithSettings:(NSMutableDictionary<NSString*, NSString*>*)settings
                            save:(void (^)(void))save {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _settings = settings;
    _save = save;
    self.title = @"Keyboard controls";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.navigationItem.rightBarButtonItem =
      [[UIBarButtonItem alloc] initWithTitle:@"Defaults"
                                       style:UIBarButtonItemStylePlain
                                      target:self
                                      action:@selector(confirmDefaults)];
}

// Sections: 0 driving, 1 menus (KeyBinds), 2 actions (ActionBinds).
- (const KeyBind&)bindAt:(NSIndexPath*)ip {
  return ip.section == 2 ? ActionBinds()[size_t(ip.row)] : KeyBinds()[size_t(ip.row)];
}

- (void)setValue:(NSString*)value forBind:(const KeyBind&)b menu:(bool)menu {
  NSString* key = KeyBindKey(b, menu);
  if ([value isEqualToString:menu ? b.menu_standard : b.standard]) {
    [_settings removeObjectForKey:key];
  } else {
    _settings[key] = value;
  }
  _save();
  [self.tableView reloadData];
}

- (void)confirmDefaults {
  UIAlertController* alert =
      [UIAlertController alertControllerWithTitle:@"Default keys for everything?"
                                          message:nil
                                   preferredStyle:UIAlertControllerStyleAlert];
  [alert addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  [alert addAction:[UIAlertAction actionWithTitle:@"Defaults"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) {
                                            for (const KeyBind& b : KeyBinds()) {
                                              [self->_settings removeObjectForKey:KeyBindKey(b, false)];
                                              [self->_settings removeObjectForKey:KeyBindKey(b, true)];
                                            }
                                            for (const KeyBind& b : ActionBinds()) {
                                              [self->_settings removeObjectForKey:KeyBindKey(b, false)];
                                            }
                                            self->_save();
                                            [self.tableView reloadData];
                                          }]];
  [self presentViewController:alert animated:YES completion:nil];
}

- (NSInteger)numberOfSectionsInTableView:(UITableView*)tableView {
  return 3;
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  return NSInteger(section == 2 ? ActionBinds().size() : KeyBinds().size());
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  return section == 0 ? @"Driving" : section == 1 ? @"Menus and pause screens" : @"Actions";
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  if (section == 0) return @"Used while you drive (free roam and races).";
  if (section == 2) return @"While driving: the in-game options' Actions on a key each (Heat ±1 in a pursuit).";
  return @"Used whenever a menu is up: the game switches between the two sets by itself. Each action "
         @"presses a controller input (shown in grey), so the game behaves as with a gamepad. Shift, "
         @"Ctrl and Alt work on their own.";
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  const KeyBind& b = [self bindAt:ip];
  const bool menu = ip.section == 1;
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleValue1
                                                 reuseIdentifier:nil];
  UIListContentConfiguration* c = UIListContentConfiguration.valueCellConfiguration;
  c.text = b.action;
  c.secondaryText = KeysForDisplay(KeyBindValue(_settings, b, menu));
  cell.contentConfiguration = c;
  UILabel* pad = [[UILabel alloc] init];
  pad.text = b.pad;
  pad.font = [UIFont preferredFontForTextStyle:UIFontTextStyleCaption1];
  pad.textColor = UIColor.tertiaryLabelColor;
  [pad sizeToFit];
  cell.accessoryView = pad;
  return cell;
}

- (void)tableView:(UITableView*)tableView didSelectRowAtIndexPath:(NSIndexPath*)ip {
  [tableView deselectRowAtIndexPath:ip animated:YES];
  const KeyBind b = [self bindAt:ip];
  const bool menu = ip.section == 1;
  NSString* current = KeyBindValue(_settings, b, menu);
  NSString* standard = menu ? b.menu_standard : b.standard;
  UIAlertController* sheet =
      [UIAlertController alertControllerWithTitle:b.action
                                          message:[NSString stringWithFormat:@"Now: %@", KeysForDisplay(current)]
                                   preferredStyle:UIAlertControllerStyleActionSheet];
  auto capture = [self, b, menu](bool add, NSString* current) {
    NFSKeyCaptureController* cap = [[NFSKeyCaptureController alloc]
        initWithPrompt:b.action
                  done:^(NSString* key) {
                    NSString* value = key;
                    if (add && current.length) {
                      NSArray* parts = [current componentsSeparatedByString:@","];
                      value = [parts containsObject:key] ? current : [current stringByAppendingFormat:@",%@", key];
                    }
                    [self setValue:value forBind:b menu:menu];
                  }];
    [self presentViewController:cap animated:YES completion:nil];
  };
  [sheet addAction:[UIAlertAction actionWithTitle:@"Set a key…"
                                            style:UIAlertActionStyleDefault
                                          handler:^(UIAlertAction*) { capture(false, current); }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Add another key…"
                                            style:UIAlertActionStyleDefault
                                          handler:^(UIAlertAction*) { capture(true, current); }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"No key"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) { [self setValue:@"" forBind:b menu:menu]; }]];
  [sheet addAction:[UIAlertAction
                       actionWithTitle:[NSString stringWithFormat:@"Default (%@)", KeysForDisplay(standard)]
                                 style:UIAlertActionStyleDefault
                               handler:^(UIAlertAction*) { [self setValue:standard forBind:b menu:menu]; }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  // On iPad an action sheet needs an anchor: the row.
  sheet.popoverPresentationController.sourceView = [tableView cellForRowAtIndexPath:ip];
  sheet.popoverPresentationController.sourceRect = [tableView cellForRowAtIndexPath:ip].bounds;
  [self presentViewController:sheet animated:YES completion:nil];
}

@end

// The launcher's navigation: portrait on iPhone, any orientation on iPad
// (the game itself is landscape only: SDL_IOS_ORIENTATIONS in ios_main).
@interface NFSLauncherNavigation : UINavigationController
@end

@implementation NFSLauncherNavigation
- (UIInterfaceOrientationMask)supportedInterfaceOrientations {
  if (self.presentedViewController && !self.presentedViewController.isBeingDismissed) {
    return self.presentedViewController.supportedInterfaceOrientations;  // e.g. the touch editor: landscape
  }
  return UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad ? UIInterfaceOrientationMaskAll
                                                                              : UIInterfaceOrientationMaskPortrait;
}
@end

@interface NFSSetupController : UIViewController
- (instancetype)initWithDisc:(BOOL)disc existing:(BOOL)existing presetsOnly:(BOOL)presetsOnly
                        saves:(UIViewController* (^)(void))saves
                       finish:(void (^)(NSInteger, NSString*, NSString*, NSInteger, NSString*, BOOL))finish;
@end

@implementation NFSSetupController {
  BOOL _disc, _presetsOnly;
  NSInteger _page, _preset, _input;
  NSInteger _renderedPage;
  NSString* _fps;
  NSString* _reflection;
  NSString* _steering;
  UIViewController* (^_saves)(void);
  void (^_finish)(NSInteger, NSString*, NSString*, NSInteger, NSString*, BOOL);
  UIStackView* _content;
  UIScrollView* _scroll;
}

- (instancetype)initWithDisc:(BOOL)disc existing:(BOOL)existing presetsOnly:(BOOL)presetsOnly
                        saves:(UIViewController* (^)(void))saves
                       finish:(void (^)(NSInteger, NSString*, NSString*, NSInteger, NSString*, BOOL))finish {
  if ((self = [super initWithNibName:nil bundle:nil])) {
    _disc = disc;
    _presetsOnly = presetsOnly;
    _page = presetsOnly ? 2 : 0;
    _preset = existing || presetsOnly ? -1 : 1;
    _input = -1;
    _renderedPage = -1;
    _fps = @"30";
    _reflection = @"half";
    _saves = [saves copy];
    _finish = [finish copy];
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.title = _presetsOnly ? @"Presets" : @"Setup";
  self.view.backgroundColor = [UIColor colorWithWhite:0.075 alpha:1];
  self.view.tintColor = nfsmw::settings_ui::Accent();
  _scroll = [[UIScrollView alloc] init];
  _scroll.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:_scroll];
  _content = [[UIStackView alloc] init];
  _content.axis = UILayoutConstraintAxisVertical;
  _content.spacing = 12;
  _content.translatesAutoresizingMaskIntoConstraints = NO;
  [_scroll addSubview:_content];
  UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
  UILayoutGuide* content = _scroll.contentLayoutGuide;
  UILayoutGuide* frame = _scroll.frameLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    [_scroll.topAnchor constraintEqualToAnchor:safe.topAnchor],
    [_scroll.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor],
    [_scroll.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor],
    [_scroll.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor],
    [_content.topAnchor constraintEqualToAnchor:content.topAnchor constant:18],
    [_content.bottomAnchor constraintEqualToAnchor:content.bottomAnchor constant:-18],
    [_content.leadingAnchor constraintEqualToAnchor:content.leadingAnchor constant:20],
    [_content.trailingAnchor constraintEqualToAnchor:content.trailingAnchor constant:-20],
    [_content.widthAnchor constraintEqualToAnchor:frame.widthAnchor constant:-40],
  ]];
  [self renderPage];
}

- (void)addLabel:(NSString*)text style:(UIFontTextStyle)style color:(UIColor*)color {
  UILabel* label = [[UILabel alloc] init];
  label.text = text;
  label.font = [UIFont preferredFontForTextStyle:style];
  label.adjustsFontForContentSizeCategory = YES;
  label.numberOfLines = 0;
  label.textColor = color;
  [_content addArrangedSubview:label];
}

- (void)addButton:(NSString*)title subtitle:(NSString*)subtitle image:(NSString*)image
         selected:(BOOL)selected action:(void (^)(void))action {
  UIButtonConfiguration* config = selected ? UIButtonConfiguration.filledButtonConfiguration
                                           : UIButtonConfiguration.tintedButtonConfiguration;
  config.title = title;
  config.subtitle = subtitle;
  config.titleAlignment = UIButtonConfigurationTitleAlignmentLeading;
  config.image = image ? [UIImage systemImageNamed:image] : nil;
  config.imagePadding = 12;
  config.contentInsets = NSDirectionalEdgeInsetsMake(10, 12, 10, 12);
  UIButton* button = [UIButton buttonWithConfiguration:config primaryAction:
      [UIAction actionWithHandler:^(__kindof UIAction*) { action(); }]];
  if (selected) button.accessibilityTraits |= UIAccessibilityTraitSelected;
  button.contentHorizontalAlignment = UIControlContentHorizontalAlignmentLeading;
  [_content addArrangedSubview:button];
}

- (void)finishAndPlay:(BOOL)play {
  _finish(_preset, _fps, _reflection, _input, _steering, play);
}

- (void)next {
  if (_presetsOnly || _page == 4) [self finishAndPlay:NO];
  else { ++_page; [self renderPage]; }
}

- (void)back {
  if (_presetsOnly) { [self dismissViewControllerAnimated:YES completion:nil]; return; }
  if (_page > 0) { --_page; [self renderPage]; }
}

- (void)skip {
  if (_page == 1) _input = -1;
  if (_page == 2) _preset = -1;
  [self next];
}

- (void)renderPage {
  for (UIView* view in _content.arrangedSubviews) [view removeFromSuperview];
  if (_renderedPage != _page) [_scroll setContentOffset:CGPointZero animated:NO];
  _renderedPage = _page;
  self.navigationItem.leftBarButtonItem = (_presetsOnly || _page > 0) ?
      [[UIBarButtonItem alloc] initWithTitle:_presetsOnly ? @"Cancel" : @"Back"
          style:UIBarButtonItemStylePlain target:self action:@selector(back)] : nil;
  self.navigationItem.rightBarButtonItem =
      [[UIBarButtonItem alloc] initWithTitle:_presetsOnly ? @"Apply" : _page == 4 ? @"Finish" : @"Continue"
          style:UIBarButtonItemStyleDone target:self action:@selector(next)];
  if (!_presetsOnly) {
    [self addLabel:[NSString stringWithFormat:@"SETUP  ·  %ld OF 5", (long)_page + 1]
        style:UIFontTextStyleCaption1 color:nfsmw::settings_ui::Accent()];
  }
  NSArray* titles = @[@"Welcome to Most Wanted", @"How do you play?", @"Look and performance",
                       @"Bring your saves", @"Ready to play"];
  [self addLabel:titles[_page] style:UIFontTextStyleTitle1 color:UIColor.labelColor];
  __weak NFSSetupController* weak = self;
  switch (_page) {
    case 0:
      [self addLabel:_disc ? @"Game disc found. You can launch from the Play tab."
                           : @"In Files, put your USA game ISO in the NFSMW app’s Documents folder."
          style:UIFontTextStyleBody color:UIColor.secondaryLabelColor];
      break;
    case 1: {
      NSArray* inputs = @[@"Touch", @"Controller", @"Keyboard and mouse"];
      NSArray* icons = @[@"hand.tap", @"gamecontroller", @"keyboard"];
      for (NSInteger i = 0; i < NSInteger(inputs.count); ++i) {
        [self addButton:inputs[i] subtitle:nil image:icons[i] selected:_input == i action:^{
          NFSSetupController* me = weak;
          if (me) { me->_input = i; [me renderPage]; }
        }];
      }
      if (_input == 0) {
        const Option* steering = FindOption(@"touch_steering");
        [self addLabel:steering->title style:UIFontTextStyleHeadline color:UIColor.labelColor];
        for (const auto& choice : steering->choices) {
          NSString* value = choice.value;
          [self addButton:choice.title subtitle:nil image:@"steeringwheel"
              selected:[(_steering ?: steering->default_value) isEqualToString:value] action:^{
                NFSSetupController* me = weak;
                if (me) { me->_steering = value; [me renderPage]; }
              }];
        }
      }
      break;
    }
    case 2: {
      NSArray* names = PresetNames();
      NSArray* summaries = @[@"Lower render resolution, half-rate reflections and Eco CPU profile.",
                             @"Original render scale and 60 fps.",
                             @"Native resolution, MSAA 4x and sharper reflections."];
      NSArray* icons = @[@"battery.100", @"gauge.with.dots.needle.50percent", @"sparkles"];
      for (NSInteger i = 0; i < NSInteger(names.count); ++i) {
        [self addButton:names[i] subtitle:summaries[i] image:icons[i] selected:_preset == i action:^{
          NFSSetupController* me = weak;
          if (me) { me->_preset = i; [me renderPage]; }
        }];
        if (i == 0 && _preset == 0) {
          [self addLabel:@"Frame rate" style:UIFontTextStyleHeadline color:UIColor.labelColor];
          for (const auto& choice : FrameRateChoices()) {
            NSString* rate = choice.value;
            if (![rate isEqualToString:@"30"] && ![rate isEqualToString:@"40"]) continue;
            [self addButton:[rate stringByAppendingString:@" fps"] subtitle:nil image:nil
                selected:[_fps isEqualToString:rate] action:^{
                  NFSSetupController* me = weak;
                  if (me) { me->_fps = rate; [me renderPage]; }
                }];
          }
          [self addLabel:@"Car reflections" style:UIFontTextStyleHeadline color:UIColor.labelColor];
          for (const auto& choice : FindOption(@"reflection_rate")->choices) {
            NSString* value = choice.value;
            NSInteger hz = [value isEqualToString:@"half"] ? _fps.integerValue / 2 : _fps.integerValue;
            NSString* subtitle = [NSString stringWithFormat:@"%ld Hz per reflection face at %@ fps",
                (long)hz, _fps];
            [self addButton:choice.title subtitle:subtitle image:nil selected:[_reflection isEqualToString:value]
                action:^{
                  NFSSetupController* me = weak;
                  if (me) { me->_reflection = value; [me renderPage]; }
                }];
          }
        }
      }
      [self addButton:@"Keep my current settings" subtitle:nil image:@"checkmark.circle" selected:_preset == -1
          action:^{
            NFSSetupController* me = weak;
            if (me) { me->_preset = -1; [me renderPage]; }
          }];
      break;
    }
    case 3: {
      [self addLabel:@"Set up iCloud sync or import a career from another device."
          style:UIFontTextStyleBody color:UIColor.secondaryLabelColor];
      [self addButton:@"Open Save Manager" subtitle:nil image:@"externaldrive" selected:NO action:^{
        NFSSetupController* me = weak;
        if (me) [me.navigationController pushViewController:me->_saves() animated:YES];
      }];
      break;
    }
    case 4:
      [self addLabel:_disc ? @"Your game disc is ready." : @"Add your game disc to enable Play."
          style:UIFontTextStyleBody color:UIColor.secondaryLabelColor];
      if (_disc) [self addButton:@"Play" subtitle:nil image:@"play.fill" selected:YES action:^{
        [weak finishAndPlay:YES];
      }];
      break;
  }
  if (!_presetsOnly && _page < 4) {
    [self addButton:@"Skip this page" subtitle:nil image:nil selected:NO action:^{ [weak skip]; }];
  }
}
@end

@interface NFSLauncherController : NFSSettingsController <UITextFieldDelegate>
- (instancetype)initWithDocuments:(fs::path)docs done:(std::function<void(fs::path)>)done;
@end

@implementation NFSLauncherController {
  fs::path _docs;
  std::function<void(fs::path)> _done;
  NSMutableDictionary<NSString*, NSString*>* _settings;
  std::vector<fs::path> _isos;
  NSString* _isoName;  // the chosen one's file name
  NSInteger _tab;      // Tab
  int _savesAttention;  // saves newer in iCloud or changed on both sides
  NSInteger _focus;
  NSTimer* _controllerTimer;
  unsigned _controllerButtons;
  UIButton* _playButton;
  std::vector<size_t> _visible;  // the Sections() shown on this tab
}

- (instancetype)initWithDocuments:(fs::path)docs done:(std::function<void(fs::path)>)done {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _docs = docs;
    _done = std::move(done);
    _settings = LoadSettings(docs);
    self.title = @"NFSMW Recompiled";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.navigationController.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  UIButtonConfiguration* play = UIButtonConfiguration.filledButtonConfiguration;
  play.title = @"Play";
  play.image = [UIImage systemImageNamed:@"play.fill"];
  play.imagePadding = 8;
  play.baseBackgroundColor = nfsmw::settings_ui::Accent();
  play.baseForegroundColor = UIColor.blackColor;
  _playButton = [UIButton buttonWithConfiguration:play primaryAction:nil];
  [_playButton addTarget:self action:@selector(play) forControlEvents:UIControlEventTouchUpInside];
  self.navigationItem.rightBarButtonItem = [[UIBarButtonItem alloc] initWithCustomView:_playButton];
  self.navigationItem.leftBarButtonItem =
      [[UIBarButtonItem alloc] initWithTitle:@"Reset"
                                       style:UIBarButtonItemStylePlain
                                      target:self
                                      action:@selector(confirmReset)];
  self.tableView.keyboardDismissMode = UIScrollViewKeyboardDismissModeOnDrag;
  _tab = [NSUserDefaults.standardUserDefaults integerForKey:@"nfsmw.launcher.tab.v2"];
  if (_tab < 0 || _tab >= kTabCount) _tab = kTabGame;
  _focus = -1;
  __weak NFSLauncherController* weak = self;
  [self installTabs:TabTitles() select:^(NSInteger tab) { [weak selectTab:tab]; }];
  [self highlightTab:_tab];
  // About: version and build, so a report names the exact build.
  UILabel* about = [[UILabel alloc] initWithFrame:CGRectMake(0, 0, 320, 56)];
  about.text = AboutText();
  about.numberOfLines = 0;
  about.textAlignment = NSTextAlignmentCenter;
  about.font = [UIFont systemFontOfSize:12];
  about.textColor = UIColor.tertiaryLabelColor;
  self.tableView.tableFooterView = about;
  // Saves: a backup of what changed, and changes from this device to iCloud.
  _savesAttention = nfsmw::saves::AutoSync(_docs);
  [self reloadTab];
  [self rescan];
  // Back from the Files app (an ISO copied in): look again.
  [NSNotificationCenter.defaultCenter addObserver:self
                                         selector:@selector(rescan)
                                             name:UIApplicationDidBecomeActiveNotification
                                           object:nil];
}

- (void)viewDidAppear:(BOOL)animated {
  [super viewDidAppear:animated];
  __weak NFSLauncherController* weak = self;
  _controllerTimer = [NSTimer scheduledTimerWithTimeInterval:1.0 / 30 repeats:YES
      block:^(NSTimer*) { [weak pollController]; }];
  if (!_settings[@"onboarding_version"]) [self openSetup:NO];
}

- (void)viewDidDisappear:(BOOL)animated {
  [super viewDidDisappear:animated];
  [_controllerTimer invalidate];
  _controllerTimer = nil;
}

- (void)openSetup:(BOOL)presetsOnly {
  if (self.presentedViewController) return;
  __weak NFSLauncherController* weak = self;
  NFSSetupController* setup = [[NFSSetupController alloc]
      initWithDisc:_isoName != nil existing:_settings.count != 0 presetsOnly:presetsOnly
      saves:^UIViewController* {
        NFSLauncherController* me = weak;
        return me ? nfsmw::saves::MakeSaveManager(me->_docs) : nil;
      }
      finish:^(NSInteger preset, NSString* fps, NSString* reflection, NSInteger input,
               NSString* steering, BOOL play) {
        NFSLauncherController* me = weak;
        if (!me) return;
        ApplyPreset(me->_settings, preset, fps, reflection);
        ApplyInputSetup(me->_settings, input, steering);
        if (!presetsOnly) me->_settings[@"onboarding_version"] = @"1";
        SaveSettings(me->_docs, me->_settings);
        [me.tableView reloadData];
        [me dismissViewControllerAnimated:YES completion:^{ if (play) [me play]; }];
      }];
  UINavigationController* navigation = [[UINavigationController alloc] initWithRootViewController:setup];
  navigation.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  navigation.modalInPresentation = YES;
  [self presentViewController:navigation animated:YES completion:nil];
}

- (void)selectTab:(NSInteger)tab {
  _tab = (tab + kTabCount) % kTabCount;
  [NSUserDefaults.standardUserDefaults setInteger:_tab forKey:@"nfsmw.launcher.tab.v2"];
  [self highlightTab:_tab];
  _focus = -1;
  [self reloadTab];
  [self.tableView setContentOffset:CGPointZero animated:NO];
}

- (void)pollController {
  GCExtendedGamepad* pad = GCController.current.extendedGamepad;
  unsigned buttons = (pad.dpad.up.pressed ? 1 : 0) | (pad.dpad.down.pressed ? 2 : 0) |
      (pad.dpad.left.pressed ? 4 : 0) | (pad.dpad.right.pressed ? 8 : 0) |
      (pad.buttonA.pressed ? 16 : 0) | (pad.leftShoulder.pressed ? 32 : 0) |
      (pad.rightShoulder.pressed ? 64 : 0) | (pad.buttonY.pressed ? 128 : 0) |
      (pad.buttonB.pressed ? 256 : 0) | (pad.buttonX.pressed ? 512 : 0);
  unsigned pressed = buttons & ~_controllerButtons;
  _controllerButtons = buttons;
  if (!pressed) return;
  if (self.presentedViewController) {
    if ((pressed & 256) && [self.presentedViewController isKindOfClass:UIAlertController.class]) {
      [self dismissViewControllerAnimated:YES completion:nil];
    }
    return;
  }
  if ((pressed & 512) && _isoName) { [self play]; return; }
  if (pressed & 256) { [self selectTab:kTabGame]; return; }
  if (pressed & (32 | 64)) { [self selectTab:_tab + (pressed & 32 ? -1 : 1)]; return; }
  NSInteger count = 0;
  for (NSInteger section = 0; section < self.tableView.numberOfSections; ++section)
    count += [self.tableView numberOfRowsInSection:section];
  if (!count) return;
  if (_focus < 0) _focus = 0;
  else if (pressed & (1 | 2)) _focus = (_focus + (pressed & 2 ? 1 : count - 1)) % count;
  NSIndexPath* path = nil;
  NSInteger row = _focus;
  for (NSInteger section = 0; section < self.tableView.numberOfSections; ++section) {
    NSInteger rows = [self.tableView numberOfRowsInSection:section];
    if (row < rows) { path = [NSIndexPath indexPathForRow:row inSection:section]; break; }
    row -= rows;
  }
  if (!path) { _focus = -1; return; }
  if (path.section < [self fixedSections]) {
    if (pressed & 16) [self tableView:self.tableView didSelectRowAtIndexPath:path];
  } else {
    const Option& option = [self sectionAt:path.section].options[size_t(path.row)];
    NSString* value = Value(_settings, option.key);
    if (pressed & 128) {
      nfsmw::settings_ui::Details(self, option.title, option.summary);
    } else if (pressed & (4 | 8 | 16)) {
      if (option.type == Type::kSwitch) {
        [self set:option.key to:[value isEqualToString:@"true"] ? @"false" : @"true"];
      } else if (option.type == Type::kChoice && !option.choices.empty()) {
        NSInteger n = NSInteger(option.choices.size());
        NSInteger i = 0;
        while (i < n && ![option.choices[size_t(i)].value isEqualToString:value]) ++i;
        i = i == n ? 0 : (i + (pressed & 4 ? n - 1 : 1)) % n;
        [self set:option.key to:option.choices[size_t(i)].value];
      } else if (pressed & 16) {
        [self tableView:self.tableView didSelectRowAtIndexPath:path];
      }
      [self.tableView reloadData];
    }
  }
  [self.tableView selectRowAtIndexPath:path animated:NO scrollPosition:UITableViewScrollPositionNone];
  [self.tableView scrollToRowAtIndexPath:path atScrollPosition:UITableViewScrollPositionNone animated:NO];
}

- (void)dealloc {
  [NSNotificationCenter.defaultCenter removeObserver:self];
}

- (void)reloadTab {
  _visible.clear();
  for (size_t i = 0; i < Sections().size(); ++i) {
    if (Sections()[i].tab == _tab) _visible.push_back(i);
  }
  if (_tab == kTabGame) {
    UILabel* brand = [[UILabel alloc] initWithFrame:CGRectMake(0, 0, 320, 78)];
    brand.text = @"  N E E D   F O R   S P E E D   /   M O S T   W A N T E D";
    brand.textColor = nfsmw::settings_ui::Accent();
    brand.backgroundColor = [UIColor colorWithRed:0.16 green:0.13 blue:0.09 alpha:1];
    brand.font = [UIFont monospacedSystemFontOfSize:14 weight:UIFontWeightBold];
    brand.adjustsFontSizeToFitWidth = YES;
    brand.minimumScaleFactor = 0.55;
    self.tableView.tableHeaderView = brand;
  } else {
    self.tableView.tableHeaderView = nil;
  }
  [self.tableView reloadData];
}

// The first sections of the Game tab are the ISO and the achievements.
- (NSInteger)fixedSections {
  return _tab == kTabGame ? 2 : 0;
}

- (const Section&)sectionAt:(NSInteger)section {
  return Sections()[_visible[size_t(section - [self fixedSections])]];
}

- (void)rescan {
  _isos = nfsmw::launcher::FindIsos(_docs);
  NSString* chosen = _settings[@"iso"];
  _isoName = nil;
  for (const fs::path& p : _isos) {
    NSString* name = [NSString stringWithUTF8String:p.filename().c_str()];
    if (!_isoName || [name isEqualToString:chosen]) {
      _isoName = name;
    }
  }
  _playButton.enabled = _isoName != nil;
  _focus = -1;
  [self.tableView reloadData];
}

- (void)set:(NSString*)key to:(NSString*)value {
  _settings[key] = value;
  SaveSettings(_docs, _settings);
}

- (void)play {
  // The ordinary Play button always starts single-player. Multiplayer is an
  // explicit action in its own screen, not a sticky mode from a previous run.
  [self set:@"lan_mode" to:@"off"];
  nfsmw::servidor::Parar();
  nfsmw::pc::Stop();
  [self launchSelectedGame];
}

- (void)launchSelectedGame {

  [self.view endEditing:YES];
  for (const fs::path& p : _isos) {
    if ([_isoName isEqualToString:[NSString stringWithUTF8String:p.filename().c_str()]]) {
      _done(p);
      return;
    }
  }
}

- (void)confirmReset {
  UIAlertController* alert =
      [UIAlertController alertControllerWithTitle:@"Reset all settings?"
                                          message:@"Every option goes back to its default. "
                                                  @"Your saves are not touched."
                                   preferredStyle:UIAlertControllerStyleAlert];
  [alert addAction:[UIAlertAction actionWithTitle:@"Cancel"
                                            style:UIAlertActionStyleCancel
                                          handler:nil]];
  [alert addAction:[UIAlertAction actionWithTitle:@"Reset"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) {
                                            NSString* iso = self->_settings[@"iso"];
                                            NSString* onboarding = self->_settings[@"onboarding_version"];
                                            [self->_settings removeAllObjects];
                                            if (onboarding) self->_settings[@"onboarding_version"] = onboarding;
                                            if (iso) {
                                              self->_settings[@"iso"] = iso;
                                            }
                                            SaveSettings(self->_docs, self->_settings);
                                            [self.tableView reloadData];
                                          }]];
  [self presentViewController:alert animated:YES completion:nil];
}

// On the Game tab, section 0 is the ISO, 1 the achievements; the rest are
// this tab's Sections().
- (NSInteger)numberOfSectionsInTableView:(UITableView*)tableView {
  return NSInteger(_visible.size()) + [self fixedSections];
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  const NSInteger fixed = [self fixedSections];
  if (fixed && section == 0) {
    return std::max<NSInteger>(1, NSInteger(_isos.size()));
  }
  if (fixed && section == 1) {
    return 1;
  }
  return NSInteger([self sectionAt:section].options.size());
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  const NSInteger fixed = [self fixedSections];
  return fixed && section == 0   ? @"ISO"
         : fixed && section == 1 ? @"Achievements"
                                 : [self sectionAt:section].title;
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  const NSInteger fixed = [self fixedSections];
  if (fixed && section == 0) {
    return _isos.empty()
               ? @"Copy your USA ISO into this app's folder (Files app › On My iPhone/iPad › "
                 @"NFSMW, or LiveContainer's folder for it). This screen looks again when you "
                 @"come back."
               : (_isos.size() > 1 ? @"Tap the one to play." : nil);
  }
  if (fixed && section == 1) {
    return nil;
  }
  if (_tab == kTabAdvanced && section == NSInteger(_visible.size()) - 1) {
    NSString* f = [self sectionAt:section].footer ?: @"";
    return [f stringByAppendingString:
                  @"Documents/extra_args.txt, if present, is applied after these settings "
                  @"and wins; Extra arguments after both."];
  }
  return [self sectionAt:section].footer;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault
                                                 reuseIdentifier:nil];
  UIListContentConfiguration* c = nfsmw::settings_ui::Content(cell, @"opticaldisc");

  const NSInteger fixed = [self fixedSections];
  if (fixed && ip.section == 0) {
    if (_isos.empty()) {
      c.text = @"No ISO found";
      c.textProperties.color = UIColor.systemOrangeColor;
      cell.selectionStyle = UITableViewCellSelectionStyleNone;
    } else {
      const fs::path& p = _isos[size_t(ip.row)];
      NSString* name = [NSString stringWithUTF8String:p.filename().c_str()];
      c.text = name;
      c.secondaryText = FileSize(p);
      cell.accessoryType = [name isEqualToString:_isoName] ? UITableViewCellAccessoryCheckmark
                                                           : UITableViewCellAccessoryNone;
    }
    cell.contentConfiguration = c;
    return cell;
  }

  if (fixed && ip.section == 1) {
    const Achievements a = LoadAchievements(_docs);
    c.image = [UIImage systemImageNamed:@"trophy.fill"];
    c.imageProperties.tintColor = UIColor.systemYellowColor;
    c.text = a.loaded ? AchievementSummary(a) : @"No list yet";
    c.secondaryText = a.loaded ? nil
                               : @"Start the game once: it brings the list of achievements "
                                 @"with it, and this shows it from then on.";
    cell.accessoryType = a.loaded ? UITableViewCellAccessoryDisclosureIndicator
                                  : UITableViewCellAccessoryNone;
    cell.selectionStyle = a.loaded ? UITableViewCellSelectionStyleDefault
                                   : UITableViewCellSelectionStyleNone;
    cell.contentConfiguration = c;
    return cell;
  }

  const Option& o = [self sectionAt:ip.section].options[size_t(ip.row)];
  c = nfsmw::settings_ui::Content(cell, o.type == Type::kLink ? @"arrow.up.right.square" :
                                      o.type == Type::kSwitch ? @"switch.2" : @"slider.horizontal.3");
  if ([o.key isEqualToString:@"saves"] && _savesAttention) {
    c.text = o.title;
    c.secondaryText = [NSString stringWithFormat:@"%d save(s) newer in iCloud or changed on two devices: "
                                                 @"open to choose which to keep.",
                                                 _savesAttention];
    c.secondaryTextProperties.color = UIColor.systemOrangeColor;
    cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
    cell.contentConfiguration = c;
    return cell;
  }
  // Greyed out: what only the emulated renderer uses while the native one
  // draws, and the native renderer's own settings while it is off.
  const bool native = On(_settings, @"native_renderer");
  const bool hud_locked = (HudDefault(o.key) || [o.key isEqualToString:@"hud_editor"]) && !On(_settings, @"hud_custom");
  const bool inactive =
      (native && EmulatorOnly(o.key)) || (!native && NativeOnly(o.key)) || hud_locked;
  c.text = o.title;
  c.secondaryText = hud_locked ? [@"Turn on Custom HUD to change. " stringByAppendingString:o.summary] : o.summary;
  cell.selectionStyle = UITableViewCellSelectionStyleDefault;
  NSString* key = o.key;
  NSString* value = Value(_settings, key);

  switch (o.type) {
    case Type::kSwitch: {
      UISwitch* sw = [[UISwitch alloc] init];
      // Settings another one decides, shown greyed out:
      //  - the single pass: always on at 19.5:9 (the wide scene is one strip),
      //    otherwise off with MSAA (it does not exist with it).
      const bool wide = [ResolvedAspect(_settings) isEqualToString:@"wide"];
      bool locked = false;
      bool on = [value isEqualToString:@"true"];
      if ([key isEqualToString:@"one_pass"] && (wide || Msaa(_settings))) {
        locked = true;
        on = wide;
      }
      locked = locked || inactive;
      sw.on = on;
      sw.enabled = !locked;
      cell.contentView.alpha = locked ? 0.45 : 1.0;
      [sw addAction:[UIAction actionWithHandler:^(UIAction*) {
            [self set:key to:sw.on ? @"true" : @"false"];
            // The native renderer greys other settings out (or back in).
            if ([key isEqualToString:@"hud_custom"]) {
              [self.tableView reloadData];
            }
          }]
          forControlEvents:UIControlEventValueChanged];
      cell.accessoryView = sw;
      break;
    }
    case Type::kChoice: {
      NSMutableArray<UIMenuElement*>* items = [NSMutableArray array];
      for (const Choice& ch : o.choices) {
        NSString* v = ch.value;
        UIAction* item = [UIAction actionWithTitle:ChoiceTitle(key, ch, _settings)
                                             image:nil
                                        identifier:nil
                                           handler:^(UIAction*) {
                                             [self set:key to:v];
                                             // Anti-aliasing and the aspect ratio
                                             // lock other settings.
                                             [self.tableView reloadData];
                                           }];
        item.state = [v isEqualToString:value] ? UIMenuElementStateOn : UIMenuElementStateOff;
        [items addObject:item];
      }
      UIButtonConfiguration* bc = UIButtonConfiguration.tintedButtonConfiguration;
      bc.indicator = UIButtonConfigurationIndicatorPopup;
      UIButton* button = [UIButton buttonWithConfiguration:bc primaryAction:nil];
      button.menu = [UIMenu menuWithChildren:items];
      button.showsMenuAsPrimaryAction = YES;
      button.changesSelectionAsPrimaryAction = YES;
      [button sizeToFit];
      button.enabled = !inactive;
      cell.contentView.alpha = inactive ? 0.45 : 1.0;
      cell.accessoryView = button;
      break;
    }
    case Type::kLink: {
      cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
      cell.selectionStyle = inactive ? UITableViewCellSelectionStyleNone : UITableViewCellSelectionStyleDefault;
      cell.contentView.alpha = inactive ? 0.45 : 1.0;
      break;
    }
    case Type::kText: {
      const bool args = [key isEqualToString:@"extra_args"];
      if (args) {  // edited full screen (didSelectRow): here how many there are
        NSArray* words = [[value componentsSeparatedByCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet]
            filteredArrayUsingPredicate:[NSPredicate predicateWithFormat:@"length > 0"]];
        c.secondaryText = words.count ? [NSString stringWithFormat:@"%lu set: %@", (unsigned long)words.count,
                                                                   [words componentsJoinedByString:@" "]]
                                      : o.summary;
        c.secondaryTextProperties.numberOfLines = 3;
        c.secondaryTextProperties.font = [UIFont monospacedSystemFontOfSize:11 weight:UIFontWeightRegular];
        cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
        cell.selectionStyle = UITableViewCellSelectionStyleDefault;
        break;
      }
      UITextField* field = [[UITextField alloc] initWithFrame:CGRectMake(0, 0, args ? 230 : 170, 34)];
      field.borderStyle = UITextBorderStyleRoundedRect;
      const bool address = [key isEqualToString:@"lan_server"];
      field.placeholder = args ? @"--option=value" : address ? @"192.168.1.10" : @"User";
      field.font = args ? [UIFont monospacedSystemFontOfSize:13 weight:UIFontWeightRegular] : field.font;
      field.smartDashesType = UITextSmartDashesTypeNo;
      field.text = value;
      field.autocorrectionType = UITextAutocorrectionTypeNo;
      field.autocapitalizationType = UITextAutocapitalizationTypeNone;
      field.spellCheckingType = UITextSpellCheckingTypeNo;
      field.smartQuotesType = UITextSmartQuotesTypeNo;
      field.returnKeyType = UIReturnKeyDone;
      field.delegate = self;
      [field addAction:[UIAction actionWithHandler:^(UIAction*) {
               // Saved as typed, but a gamertag only while it is valid for Xbox 360.
               const bool valid = args || address || GamertagValid(field.text);
               field.textColor = valid ? UIColor.labelColor : UIColor.systemRedColor;
               if (valid) {
                 [self set:key to:field.text];
               }
             }]
          forControlEvents:UIControlEventEditingChanged];
      cell.accessoryView = field;
      break;
    }
  }
  cell.contentConfiguration = c;
  if ([key isEqualToString:@"preset"]) {
    UILabel* preset = [[UILabel alloc] init];
    preset.text = PresetName(_settings);
    preset.textColor = nfsmw::settings_ui::Accent();
    [preset sizeToFit];
    cell.accessoryView = preset;
  }
  nfsmw::settings_ui::RowDetails(cell, self, o.title, o.summary);
  return cell;
}

- (BOOL)textFieldShouldReturn:(UITextField*)field {
  [field resignFirstResponder];
  return YES;
}

- (void)tableView:(UITableView*)tableView didSelectRowAtIndexPath:(NSIndexPath*)ip {
  [tableView deselectRowAtIndexPath:ip animated:YES];
  const NSInteger fixed = [self fixedSections];
  if (fixed && ip.section == 1) {
    Achievements a = LoadAchievements(_docs);
    if (a.loaded) {
      [self.navigationController
          pushViewController:[[NFSAchievementsController alloc] initWithAchievements:std::move(a)]
                    animated:YES];
    }
    return;
  }
  if (ip.section >= fixed) {
    const Option& o = [self sectionAt:ip.section].options[size_t(ip.row)];
    if ([o.key isEqualToString:@"setup_again"] || [o.key isEqualToString:@"preset"]) {
      [self openSetup:[o.key isEqualToString:@"preset"]];
      return;
    }
    if (o.type == Type::kLink && [o.key isEqualToString:@"multiplayer_setup"]) {
      if (!_isoName) {
        UIAlertController* alert = [UIAlertController alertControllerWithTitle:@"Choose a game first"
            message:@"Add your USA game ISO and select it before opening multiplayer."
            preferredStyle:UIAlertControllerStyleAlert];
        [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
        [self presentViewController:alert animated:YES completion:nil];
        return;
      }
      [self.navigationController pushViewController:nfsmw::lan::MakeSetup(_docs, _settings,
          [self] { [self launchSelectedGame]; }) animated:YES];
      return;
    }
    if (o.type == Type::kText && [o.key isEqualToString:@"extra_args"]) {
      NSString* key = o.key;
      [self.navigationController
          pushViewController:[[NFSArgumentsEditorController alloc] initWithText:Value(_settings, key)
                                                                        changed:^(NSString* text) {
                                                                          [self set:key to:text];
                                                                          [self.tableView reloadData];
                                                                        }]
                    animated:YES];
      return;
    }
    if (o.type == Type::kLink && [o.key isEqualToString:@"saves"]) {
      [self.navigationController pushViewController:nfsmw::saves::MakeSaveManager(_docs) animated:YES];
      return;
    }
    if (o.type == Type::kLink && [o.key isEqualToString:@"hud_editor"]) {
      if (!On(_settings, @"hud_custom")) return;  // greyed out
      [self presentViewController:nfsmw::hud::MakeEditor(_settings,
                                                          ^{
                                                            SaveSettings(self->_docs, self->_settings);
                                                          })
                         animated:YES
                       completion:nil];
      return;
    }
    if (o.type == Type::kLink && [o.key isEqualToString:@"touch_layout"]) {
      [self presentViewController:nfsmw::touch::MakeLayoutEditor(Value(_settings, @"touch_steering")) animated:YES completion:nil];
      return;
    }
    if (o.type == Type::kLink && [o.key isEqualToString:@"keyboard_bindings"]) {
      NFSKeyBindsController* editor =
          [[NFSKeyBindsController alloc] initWithSettings:_settings
                                                     save:^{
                                                       SaveSettings(self->_docs, self->_settings);
                                                     }];
      [self.navigationController pushViewController:editor animated:YES];
    }
    return;
  }
  if (fixed && ip.section == 0 && size_t(ip.row) < _isos.size()) {
    _isoName = [NSString stringWithUTF8String:_isos[size_t(ip.row)].filename().c_str()];
    [self set:@"iso" to:_isoName];
    [tableView reloadSections:[NSIndexSet indexSetWithIndex:0]
             withRowAnimation:UITableViewRowAnimationNone];
  }
}

@end

// ---------------------------------------------------------------------------
//  The API
// ---------------------------------------------------------------------------
namespace nfsmw::launcher {

fs::path Documents() {
  NSArray<NSString*>* paths =
      NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES);
  return fs::path(paths.firstObject.UTF8String);
}

std::vector<fs::path> FindIsos(const fs::path& documents) {
  std::vector<fs::path> isos;
  std::error_code ec;
  for (const auto& e : fs::directory_iterator(documents, ec)) {
    std::string ext = e.path().extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    if (e.is_regular_file(ec) && ext == ".iso") {
      isos.push_back(e.path());
    }
  }
  std::sort(isos.begin(), isos.end());
  return isos;
}

fs::path Run(const fs::path& documents) {
  bool finished = false;
  fs::path chosen;
  NFSLauncherController* root =
      [[NFSLauncherController alloc] initWithDocuments:documents
                                                  done:[&](fs::path iso) {
                                                    chosen = iso;
                                                    finished = true;
                                                  }];
  UINavigationController* nav = [[NFSLauncherNavigation alloc] initWithRootViewController:root];
  nav.navigationBar.prefersLargeTitles = YES;

  // The app's own scene, not an external display's (AirPlay, HDMI).
  UIWindowScene* scene = nfsmw::AppScene();
  UIWindow* window = scene ? [[UIWindow alloc] initWithWindowScene:scene]
                           : [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
  window.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  window.windowLevel = UIWindowLevelNormal + 1;  // over SDL's launch screen
  window.rootViewController = nav;
  [window makeKeyAndVisible];

  while (!finished) {
    @autoreleasepool {
      [NSRunLoop.currentRunLoop runMode:NSDefaultRunLoopMode beforeDate:NSDate.distantFuture];
    }
  }

  window.hidden = YES;
  window.rootViewController = nil;
  window = nil;
  // With AirPlay mirroring on, a second window still holding the launcher
  // stayed visible over the game on the phone (nfsmw_airplay4.log): every
  // window with the launcher goes, and SDL's becomes the key one again.
  for (UIScene* s in UIApplication.sharedApplication.connectedScenes) {
    if (![s isKindOfClass:UIWindowScene.class]) continue;
    for (UIWindow* w in ((UIWindowScene*)s).windows) {
      if ([w.rootViewController isKindOfClass:NFSLauncherNavigation.class]) {
        w.hidden = YES;
        w.rootViewController = nil;
      } else if ([NSStringFromClass(w.rootViewController.class) hasPrefix:@"SDL"]) {
        [w makeKeyAndVisible];
      }
    }
  }
  // Back to landscape for the game: the launcher may have left the scene in
  // portrait, and iOS only re-evaluates orientations when asked.
  if (scene) {
    for (UIWindow* w in scene.windows) {
      [w.rootViewController setNeedsUpdateOfSupportedInterfaceOrientations];
    }
    UIWindowSceneGeometryPreferencesIOS* prefs = [[UIWindowSceneGeometryPreferencesIOS alloc]
        initWithInterfaceOrientations:UIInterfaceOrientationMaskLandscape];
    [scene requestGeometryUpdateWithPreferences:prefs errorHandler:nil];
  }
  return chosen;
}

std::vector<std::string> SettingsArguments(const fs::path& documents) {
  return Arguments(LoadSettings(documents));
}

// The menu key set, "keybind_a=Return,Space;keybind_b=..." (keyboard_context.cpp).
// Read from settings.json by the game itself: as a command-line value
// (--nfsmw_menu_keybinds) it arrived empty (dev13 log: "one set of keys").
std::string MenuKeyBinds() {
  NSDictionary<NSString*, NSString*>* s = LoadSettings(Documents());
  std::string list;
  for (const KeyBind& kb : KeyBinds()) {
    list += std::string(list.empty() ? "" : ";") + kb.setting.UTF8String + "=" + KeyBindValue(s, kb, true).UTF8String;
  }
  return list;
}

// The action keys, "action_reset_car=1;..." (keyboard_prompts.mm).
std::string ActionKeyBinds() {
  NSDictionary<NSString*, NSString*>* s = LoadSettings(Documents());
  std::string list;
  for (const KeyBind& kb : ActionBinds()) {
    list += std::string(list.empty() ? "" : ";") + kb.setting.UTF8String + "=" + KeyBindValue(s, kb).UTF8String;
  }
  return list;
}

NSString* KeyNameForHID(long usage) { return KeyName(UIKeyboardHIDUsage(usage)); }

// The driving set, the same way (the in-game keyboard editor applies both).
std::string DrivingKeyBinds() {
  NSDictionary<NSString*, NSString*>* s = LoadSettings(Documents());
  std::string list;
  for (const KeyBind& kb : KeyBinds()) {
    list += std::string(list.empty() ? "" : ";") + kb.setting.UTF8String + "=" + KeyBindValue(s, kb).UTF8String;
  }
  return list;
}

UIViewController* MakeKeyBindsEditor(NSMutableDictionary<NSString*, NSString*>* settings, void (^save)(void)) {
  return [[NFSKeyBindsController alloc] initWithSettings:settings save:save];
}

std::vector<MenuRow> Rows(NSArray<NSString*>* keys) {
  std::vector<MenuRow> rows;
  for (NSString* key in keys) {
    const Option* o = FindOption(key);
    if (!o || (o->type != Type::kSwitch && o->type != Type::kChoice)) continue;
    MenuRow r{o->key, o->title, o->summary, o->type == Type::kSwitch, {}};
    NSDictionary<NSString*, NSString*>* s = LoadSettings(Documents());
    for (const Choice& c : o->choices) r.choices.emplace_back(ChoiceTitle(o->key, c, s), c.value);
    rows.push_back(std::move(r));
  }
  return rows;
}

std::vector<MenuGroup> Groups(NSArray<NSString*>* keys) {
  NSSet* wanted = [NSSet setWithArray:keys];
  NSDictionary<NSString*, NSString*>* settings = LoadSettings(Documents());
  std::vector<MenuGroup> groups;
  for (NSInteger tab = 0; tab < kTabCount; ++tab) {
    for (const Section& section : Sections()) {
      if (section.tab != tab) continue;
      MenuGroup g{TabTitles()[tab], section.title, {}};
      for (const Option& o : section.options) {
        if (![wanted containsObject:o.key]) continue;
        MenuRow r{o.key, o.title, o.summary, o.type == Type::kSwitch, {}, o.type == Type::kLink};
        for (const Choice& c : o.choices) r.choices.emplace_back(ChoiceTitle(o.key, c, settings), c.value);
        g.rows.push_back(std::move(r));
      }
      if (!g.rows.empty()) groups.push_back(std::move(g));
    }
  }
  return groups;
}

NSArray<NSString*>* InGameKeys() {
  NSMutableArray<NSString*>* keys = [NSMutableArray array];
  for (const Section& section : Sections()) {
    for (const Option& o : section.options) {
      if (o.flags & kInGame) [keys addObject:o.key];
    }
  }
  return keys;
}

bool InGameNeedsNative(NSString* key) { return HasFlag(key, kInGameNative); }

const std::set<std::string>& LiveCvars() {
  static const std::set<std::string> cvars = [] {
    std::set<std::string> c;
    for (const Section& section : Sections()) {
      for (const Option& o : section.options) {
        if (!o.live) continue;
        std::string list = o.live;
        for (size_t at = 0; at <= list.size();) {
          const size_t comma = std::min(list.find(',', at), list.size());
          if (comma > at) c.insert(list.substr(at, comma - at));
          at = comma + 1;
        }
      }
    }
    return c;
  }();
  return cvars;
}

NSMutableDictionary<NSString*, NSString*>* ReadSettings(const fs::path& documents) { return LoadSettings(documents); }

void WriteSettings(const fs::path& documents, NSDictionary<NSString*, NSString*>* settings) {
  SaveSettings(documents, settings);
}

NSString* SettingValue(NSDictionary<NSString*, NSString*>* settings, NSString* key) { return Value(settings, key); }

bool HudLocked(NSDictionary<NSString*, NSString*>* settings, NSString* key) {
  return HudDefault(key) && !On(settings, @"hud_custom");
}

std::vector<std::string> ArgumentsFor(NSDictionary<NSString*, NSString*>* settings) { return Arguments(settings); }

}  // namespace nfsmw::launcher
