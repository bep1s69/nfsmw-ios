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
  _tabScroll.backgroundColor = [UIColor colorWithRed:0.13 green:0.14 blue:0.16 alpha:1];
  _tabScroll.showsHorizontalScrollIndicator = NO;
  _tabs = [[UIStackView alloc] init];
  _tabs.spacing = 0;
  _tabs.translatesAutoresizingMaskIntoConstraints = NO;
  [_tabScroll addSubview:_tabs];
  [_layout insertArrangedSubview:_tabScroll atIndex:0];
  _railWidth = [_tabScroll.widthAnchor constraintEqualToConstant:136];
  _stripHeight = [_tabScroll.heightAnchor constraintEqualToConstant:44];
  UILayoutGuide* content = _tabScroll.contentLayoutGuide;
  UILayoutGuide* frame = _tabScroll.frameLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    [_tabs.leadingAnchor constraintEqualToAnchor:content.leadingAnchor constant:4],
    [_tabs.trailingAnchor constraintEqualToAnchor:content.trailingAnchor constant:-4],
    [_tabs.topAnchor constraintEqualToAnchor:content.topAnchor],
    [_tabs.bottomAnchor constraintEqualToAnchor:content.bottomAnchor],
  ]];
  UIView* divider = [[UIView alloc] init];
  divider.backgroundColor = [UIColor colorWithWhite:0.30 alpha:1];
  divider.userInteractionEnabled = NO;
  divider.translatesAutoresizingMaskIntoConstraints = NO;
  [_tabScroll addSubview:divider];
  _railConstraints = @[
    _railWidth, [_tabs.widthAnchor constraintEqualToAnchor:frame.widthAnchor constant:-8],
    [divider.trailingAnchor constraintEqualToAnchor:frame.trailingAnchor],
    [divider.topAnchor constraintEqualToAnchor:frame.topAnchor],
    [divider.bottomAnchor constraintEqualToAnchor:frame.bottomAnchor],
    [divider.widthAnchor constraintEqualToConstant:1],
  ];
  _stripConstraints = @[
    _stripHeight, [_tabs.heightAnchor constraintEqualToAnchor:frame.heightAnchor],
    [divider.leadingAnchor constraintEqualToAnchor:frame.leadingAnchor],
    [divider.trailingAnchor constraintEqualToAnchor:frame.trailingAnchor],
    [divider.bottomAnchor constraintEqualToAnchor:frame.bottomAnchor],
    [divider.heightAnchor constraintEqualToConstant:1],
  ];
  for (NSString* title in titles) {
    NSInteger index = _tabs.arrangedSubviews.count;
    UIButtonConfiguration* config = UIButtonConfiguration.plainButtonConfiguration;
    config.title = title;
    config.contentInsets = NSDirectionalEdgeInsetsMake(0, 6, 0, 6);
    config.titleTextAttributesTransformer = ^NSDictionary* (NSDictionary* attributes) {
      NSMutableDictionary* compact = [attributes mutableCopy];
      compact[NSFontAttributeName] = [UIFont preferredFontForTextStyle:UIFontTextStyleSubheadline];
      return compact;
    };
    UIButton* button = [UIButton buttonWithConfiguration:config primaryAction:
        [UIAction actionWithHandler:^(__kindof UIAction*) { select(index); }]];
    [button.heightAnchor constraintGreaterThanOrEqualToConstant:44].active = YES;
    [button.widthAnchor constraintGreaterThanOrEqualToConstant:44].active = YES;
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
  UIButton* active = nil;
  NSInteger i = 0;
  for (UIButton* button in _tabs.arrangedSubviews) {
    const BOOL selected = i++ == index;
    UIButtonConfiguration* config = button.configuration;
    config.baseForegroundColor = selected ? nfsmw::settings_ui::Accent() : UIColor.labelColor;
    config.background.backgroundColor = selected ? [nfsmw::settings_ui::Accent() colorWithAlphaComponent:0.20]
                                                 : UIColor.clearColor;
    config.background.cornerRadius = 4;
    config.background.backgroundInsets = NSDirectionalEdgeInsetsMake(8, 1, 8, 1);
    button.contentHorizontalAlignment = _railWidth.active ? UIControlContentHorizontalAlignmentLeading
                                                         : UIControlContentHorizontalAlignmentCenter;
    button.configuration = config;
    button.accessibilityTraits = UIAccessibilityTraitButton | (selected ? UIAccessibilityTraitSelected : 0);
    if (selected) active = button;
  }
  if (active) {
    [_tabScroll layoutIfNeeded];
    [_tabScroll scrollRectToVisible:[active convertRect:active.bounds toView:_tabScroll] animated:NO];
  }
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section { return 0; }
- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)path {
  return [[UITableViewCell alloc] init];
}
@end
