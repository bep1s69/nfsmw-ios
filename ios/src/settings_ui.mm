#import "settings_ui.h"

@implementation NFSSettingsController {
  UITableViewStyle _style;
  UIStackView* _layout;
  UIStackView* _tabs;
  UIScrollView* _tabScroll;
  NSLayoutConstraint* _railWidth;
  NSLayoutConstraint* _stripHeight;
  NSArray<NSLayoutConstraint*>* _railConstraints;
  NSArray<NSLayoutConstraint*>* _stripConstraints;
  NSInteger _selectedTab;
}

- (instancetype)initWithStyle:(UITableViewStyle)style {
  if ((self = [super initWithNibName:nil bundle:nil])) _style = style;
  return self;
}

- (void)loadView {
  self.view = [[UIView alloc] init];
  self.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  self.view.backgroundColor = [UIColor colorWithWhite:0.075 alpha:0.93];
  self.view.tintColor = nfsmw::settings_ui::Accent();
  _tableView = [[UITableView alloc] initWithFrame:CGRectZero style:_style];
  _tableView.backgroundColor = UIColor.clearColor;
  _tableView.delegate = self;
  _tableView.dataSource = self;
  _layout = [[UIStackView alloc] initWithArrangedSubviews:@[_tableView]];
  _layout.axis = UILayoutConstraintAxisVertical;
  _layout.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:_layout];
  UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    [_layout.topAnchor constraintEqualToAnchor:safe.topAnchor],
    [_layout.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor],
    [_layout.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor],
    [_layout.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor],
  ]];
}

- (void)installTabs:(NSArray<NSString*>*)titles select:(void (^)(NSInteger))select {
  _tabScroll = [[UIScrollView alloc] init];
  _tabScroll.backgroundColor = [UIColor colorWithWhite:0.11 alpha:0.97];
  _tabScroll.showsHorizontalScrollIndicator = NO;
  _tabs = [[UIStackView alloc] init];
  _tabs.spacing = 5;
  _tabs.translatesAutoresizingMaskIntoConstraints = NO;
  [_tabScroll addSubview:_tabs];
  [_layout insertArrangedSubview:_tabScroll atIndex:0];
  _railWidth = [_tabScroll.widthAnchor constraintEqualToConstant:164];
  _stripHeight = [_tabScroll.heightAnchor constraintEqualToConstant:54];
  UILayoutGuide* content = _tabScroll.contentLayoutGuide;
  UILayoutGuide* frame = _tabScroll.frameLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    [_tabs.leadingAnchor constraintEqualToAnchor:content.leadingAnchor constant:8],
    [_tabs.trailingAnchor constraintEqualToAnchor:content.trailingAnchor constant:-8],
    [_tabs.topAnchor constraintEqualToAnchor:content.topAnchor constant:5],
    [_tabs.bottomAnchor constraintEqualToAnchor:content.bottomAnchor constant:-5],
  ]];
  _railConstraints = @[_railWidth, [_tabs.widthAnchor constraintEqualToAnchor:frame.widthAnchor constant:-16]];
  _stripConstraints = @[_stripHeight, [_tabs.heightAnchor constraintEqualToAnchor:frame.heightAnchor constant:-10]];
  for (NSString* title in titles) {
    NSInteger index = _tabs.arrangedSubviews.count;
    UIButtonConfiguration* config = UIButtonConfiguration.tintedButtonConfiguration;
    config.title = title;
    UIButton* button = [UIButton buttonWithConfiguration:config primaryAction:
        [UIAction actionWithHandler:^(__kindof UIAction*) { select(index); }]];
    [button.heightAnchor constraintGreaterThanOrEqualToConstant:44].active = YES;
    [_tabs addArrangedSubview:button];
  }
  [self highlightTab:_selectedTab];
}

- (void)viewDidLayoutSubviews {
  [super viewDidLayoutSubviews];
  if (!_tabScroll) return;
  const BOOL wide = self.view.safeAreaLayoutGuide.layoutFrame.size.width >= 700;
  if ((!_railWidth.active && !_stripHeight.active) || wide != _railWidth.active) {
    [NSLayoutConstraint deactivateConstraints:wide ? _stripConstraints : _railConstraints];
    _layout.axis = wide ? UILayoutConstraintAxisHorizontal : UILayoutConstraintAxisVertical;
    _tabs.axis = wide ? UILayoutConstraintAxisVertical : UILayoutConstraintAxisHorizontal;
    [NSLayoutConstraint activateConstraints:wide ? _railConstraints : _stripConstraints];
    [self highlightTab:_selectedTab];
  }
}

- (void)highlightTab:(NSInteger)index {
  _selectedTab = index;
  NSInteger i = 0;
  for (UIButton* button in _tabs.arrangedSubviews) {
    const BOOL selected = i++ == index;
    UIButtonConfiguration* config = button.configuration;
    config.baseForegroundColor = selected ? nfsmw::settings_ui::Accent() : UIColor.labelColor;
    button.configuration = config;
    button.accessibilityTraits = UIAccessibilityTraitButton | (selected ? UIAccessibilityTraitSelected : 0);
    if (selected) {
      [_tabScroll layoutIfNeeded];
      [_tabScroll scrollRectToVisible:[button convertRect:button.bounds toView:_tabScroll] animated:NO];
    }
  }
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section { return 0; }
- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)path {
  return [[UITableViewCell alloc] init];
}
@end
