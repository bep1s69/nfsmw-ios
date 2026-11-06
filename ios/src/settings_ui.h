#pragma once

#import <UIKit/UIKit.h>

namespace nfsmw::settings_ui {
inline UIColor* Accent() {
  return [UIColor colorWithRed:0.96 green:0.76 blue:0.39 alpha:1];
}

inline UIListContentConfiguration* Content(UITableViewCell* cell, NSString* icon) {
  cell.backgroundColor = [UIColor colorWithWhite:0.13 alpha:0.96];
  UIView* focus = [[UIView alloc] init];
  focus.backgroundColor = [Accent() colorWithAlphaComponent:0.16];
  focus.layer.cornerRadius = 9;
  focus.layer.borderWidth = 2;
  focus.layer.borderColor = Accent().CGColor;
  cell.selectedBackgroundView = focus;
  UIListContentConfiguration* c = UIListContentConfiguration.subtitleCellConfiguration;
  c.image = [UIImage systemImageNamed:icon];
  c.imageProperties.tintColor = Accent();
  c.secondaryTextProperties.color = UIColor.secondaryLabelColor;
  c.secondaryTextProperties.numberOfLines = 1;
  c.textToSecondaryTextVerticalPadding = 3;
  return c;
}

inline void Details(UIViewController* host, NSString* title, NSString* summary) {
  UIAlertController* alert = [UIAlertController alertControllerWithTitle:title message:summary
      preferredStyle:UIAlertControllerStyleAlert];
  [alert addAction:[UIAlertAction actionWithTitle:@"Done" style:UIAlertActionStyleCancel handler:nil]];
  [host presentViewController:alert animated:YES completion:nil];
}

inline void RowDetails(UITableViewCell* cell, UIViewController* host, NSString* title, NSString* summary) {
  if (!summary.length) return;
  __weak UIViewController* weakHost = host;
  UIAction* detail = [UIAction actionWithTitle:@"Details" image:[UIImage systemImageNamed:@"info.circle"]
      identifier:nil handler:^(__kindof UIAction*) {
        UIViewController* presenter = weakHost;
        if (presenter) Details(presenter, title, summary);
      }];
  UIButton* info = [UIButton systemButtonWithImage:[UIImage systemImageNamed:@"info.circle"]
      target:nil action:nil];
  info.accessibilityLabel = [NSString stringWithFormat:@"%@ details", title];
  [info addAction:detail forControlEvents:UIControlEventTouchUpInside];
  [info.widthAnchor constraintEqualToConstant:44].active = YES;
  [info.heightAnchor constraintGreaterThanOrEqualToConstant:44].active = YES;
  UIView* accessory = cell.accessoryView;
  if (!accessory && cell.accessoryType == UITableViewCellAccessoryDisclosureIndicator) {
    accessory = [[UIImageView alloc] initWithImage:[UIImage systemImageNamed:@"chevron.right"]];
    accessory.tintColor = UIColor.secondaryLabelColor;
  }
  UIStackView* stack = [[UIStackView alloc] initWithArrangedSubviews:accessory ? @[accessory, info] : @[info]];
  stack.alignment = UIStackViewAlignmentCenter;
  CGSize size = [stack systemLayoutSizeFittingSize:UILayoutFittingCompressedSize];
  stack.frame = CGRectMake(0, 0, size.width, size.height);
  cell.accessoryType = UITableViewCellAccessoryNone;
  cell.accessoryView = stack;
}
}

@interface NFSSettingsController : UIViewController <UITableViewDataSource, UITableViewDelegate>
@property(nonatomic, readonly) UITableView* tableView;
- (instancetype)initWithStyle:(UITableViewStyle)style;
- (void)installTabs:(NSArray<NSString*>*)titles select:(void (^)(NSInteger))select;
- (void)highlightTab:(NSInteger)index;
@end
