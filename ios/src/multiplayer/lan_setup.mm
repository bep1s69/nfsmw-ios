// Native Host/Join flow using victorgbd's unchanged lobby and discovery protocol.
#import <UIKit/UIKit.h>
#include "lan_setup.h"
#include "lan_session.h"
#include "red_lan.h"
#include "servidor_ea.h"
#include "../launcher.h"
#include "../boot_trace.h"
#include <regex>

namespace {
dispatch_queue_t SetupQueue() {
  static dispatch_queue_t queue = dispatch_queue_create("nfsmw.lan.setup", DISPATCH_QUEUE_SERIAL);
  return queue;
}
NSString* Text(const std::string& s) { return [NSString stringWithUTF8String:s.c_str()] ?: @""; }
std::string Bytes(NSString* s) { return std::string(s.UTF8String ?: ""); }
bool ValidName(NSString* value) {
  static const std::regex pattern("[A-Za-z][A-Za-z0-9 ]{0,14}");
  return std::regex_match(Bytes(value), pattern);
}
NSString* DefaultName() {
  std::string ip = nfsmw::red::IpLocal();
  auto last = ip.find_last_of('.');
  return [NSString stringWithFormat:@"%@%s", UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad ? @"iPad" : @"iPhone",
          (last == std::string::npos ? std::string() : ip.substr(last + 1)).c_str()];
}
}

@interface NFSLanSetupController : UITableViewController <UITextFieldDelegate>
- (instancetype)initWithDocuments:(std::filesystem::path)docs
                         settings:(NSMutableDictionary<NSString*, NSString*>*)settings
                           launch:(std::function<void()>)launch;
@end

@implementation NFSLanSetupController {
  std::filesystem::path _docs;
  NSMutableDictionary<NSString*, NSString*>* _settings;
  std::function<void()> _launch;
  UITextField* _name;
  NSString* _role;
  NSString* _status;
  NSString* _endpoint;
  NSString* _serverName;
  NSString* _preparedName;
  std::vector<nfsmw::red::Encontrado> _hosts;
  NSUInteger _generation;
  BOOL _busy, _ready, _closing, _launching;
  NSTimer* _timer;
}

- (instancetype)initWithDocuments:(std::filesystem::path)docs
                         settings:(NSMutableDictionary<NSString*, NSString*>*)settings
                           launch:(std::function<void()>)launch {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _docs = docs; _settings = settings; _launch = std::move(launch);
    _status = @"Choose Host on one device and Join on the other. Both devices must use the same Wi-Fi.";
    _endpoint = @"";
    _serverName = @"";
    _settings[@"lan_mode"] = @"off";  // setup itself never launches the game
    nfsmw::launcher::WriteSettings(_docs, _settings);
    self.title = @"Multiplayer";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.navigationItem.rightBarButtonItem = [[UIBarButtonItem alloc] initWithTitle:@"Launch game"
      style:UIBarButtonItemStyleDone target:self action:@selector(launchGame)];
  self.navigationItem.rightBarButtonItem.enabled = NO;
  self.tableView.keyboardDismissMode = UIScrollViewKeyboardDismissModeOnDrag;
  _name = [[UITextField alloc] initWithFrame:CGRectMake(0,0,170,34)];
  _name.borderStyle = UITextBorderStyleRoundedRect;
  _name.autocorrectionType = UITextAutocorrectionTypeNo;
  _name.autocapitalizationType = UITextAutocapitalizationTypeNone;
  _name.smartQuotesType = UITextSmartQuotesTypeNo;
  _name.smartDashesType = UITextSmartDashesTypeNo;
  _name.returnKeyType = UIReturnKeyDone;
  _name.delegate = self;
  _name.text = _settings[@"lan_gamertag"];
  if (!ValidName(_name.text)) _name.text = DefaultName();
  [self saveName];
  __weak NFSLanSetupController* weakSelf = self;
  [_name addAction:[UIAction actionWithHandler:^(UIAction*) {
    NFSLanSetupController* self = weakSelf;
    if (!self) return;
    self->_name.textColor = ValidName(self->_name.text) ? UIColor.labelColor : UIColor.systemRedColor;
    if (self->_ready && ![self->_name.text isEqualToString:self->_preparedName]) {
      self->_ready = NO;
      self->_generation++;
      self->_status = @"Name changed. Tap Host or Join again to reconnect.";
      dispatch_async(SetupQueue(), ^{ nfsmw::servidor::Parar(); });
      self.navigationItem.rightBarButtonItem.enabled = NO;
      [self.tableView reloadSections:[NSIndexSet indexSetWithIndexesInRange:NSMakeRange(2,3)] withRowAnimation:UITableViewRowAnimationNone];
    }
  }] forControlEvents:UIControlEventEditingChanged];
  _timer = [NSTimer scheduledTimerWithTimeInterval:1 repeats:YES block:^(NSTimer*) {
    NFSLanSetupController* self = weakSelf;
    if (!self || !self->_ready || ![self->_role isEqualToString:@"host"]) return;
    if (!nfsmw::servidor::EnMarcha()) {
      self->_ready = NO;
      self->_status = @"The lobby stopped. Tap Host to start it again.";
      [self refresh];
    } else if (![Text(nfsmw::red::IpLocal()) isEqualToString:self->_endpoint]) {
      self->_ready = NO; self->_generation++;
      self->_status = @"Your Wi-Fi address changed. Tap Host to reconnect.";
      dispatch_async(SetupQueue(), ^{ nfsmw::servidor::Parar(); });
      [self refresh];
    }
  }];
}

- (void)refresh {
  self.navigationItem.rightBarButtonItem.enabled = _ready && !_busy;
  [self.tableView reloadData];
}
- (void)launchGame {
  if (_ready && !_busy) [self connectAndLaunch:YES restartHost:NO];
}

- (void)viewWillDisappear:(BOOL)animated {
  [super viewWillDisappear:animated];
  if (self.isMovingFromParentViewController && !_launching) {
    _closing = YES; _generation++;
    _settings[@"lan_mode"] = @"off";
    nfsmw::launcher::WriteSettings(_docs, _settings);
    dispatch_async(SetupQueue(), ^{ nfsmw::servidor::Parar(); });
    [_timer invalidate];
  }
}
- (void)dealloc { [_timer invalidate]; }
- (BOOL)textFieldShouldReturn:(UITextField*)field { [field resignFirstResponder]; return YES; }
- (void)saveName {
  _settings[@"lan_gamertag"] = _name.text ?: @"";
  nfsmw::launcher::WriteSettings(_docs, _settings);
}
- (BOOL)checkName {
  [self.view endEditing:YES];
  if (!ValidName(_name.text)) {
    _status = @"Use 1–15 letters, numbers or spaces for your player name, starting with a letter.";
    [self refresh]; return NO;
  }
  [self saveName]; return YES;
}

- (void)chooseHost {
  if (_busy || ![self checkName]) return;
  _role = @"host"; _hosts.clear();
  _endpoint = Text(nfsmw::red::IpLocal()); _serverName = _name.text;
  [self connectAndLaunch:NO restartHost:YES];
}

- (void)search {
  if (_busy || ![self checkName]) return;
  _role = @"join"; _ready = NO; _busy = YES; _hosts.clear();
  _status = @"Looking for other devices hosting on your Wi-Fi…";
  const NSUInteger generation = ++_generation;
  nfsmw::boot::Trace("[lan-setup] searching for another host");
  [self refresh];
  dispatch_async(SetupQueue(), ^{
    nfsmw::servidor::Parar();  // never list this device as a join target
    const auto found = nfsmw::red::BuscarServidores();
    dispatch_async(dispatch_get_main_queue(), ^{
      if (self->_closing || generation != self->_generation) return;
      self->_busy = NO;
      if (found) self->_hosts = *found;
      self->_status = !found ? @"No local Wi-Fi connection. Connect both devices to the same Wi-Fi and try again."
        : self->_hosts.empty() ? @"No hosts found. On the other device, open Multiplayer and tap Host. Keep it open, then search again. You can also enter its address below."
        : @"Tap the host on the other device to join its lobby.";
      nfsmw::boot::Trace("[lan-setup] search found " + std::to_string(self->_hosts.size()) + " remote hosts");
      [self refresh];
    });
  });
}

- (void)manualAddress {
  if (_busy) return;
  UIAlertController* alert = [UIAlertController alertControllerWithTitle:@"Join by address"
      message:@"Enter the address shown by Host on the OTHER device."
      preferredStyle:UIAlertControllerStyleAlert];
  [alert addTextFieldWithConfigurationHandler:^(UITextField* f) {
    f.placeholder = @"192.168.1.10"; f.text = self->_settings[@"lan_server"];
    f.autocorrectionType = UITextAutocorrectionTypeNo;
    f.autocapitalizationType = UITextAutocapitalizationTypeNone;
  }];
  [alert addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  [alert addAction:[UIAlertAction actionWithTitle:@"Connect" style:UIAlertActionStyleDefault handler:^(UIAlertAction*) {
    self->_role = @"join";
    self->_endpoint = [alert.textFields.firstObject.text stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
    self->_serverName = @"LAN host";
    [self connectAndLaunch:NO restartHost:NO];
  }]];
  [self presentViewController:alert animated:YES completion:nil];
}

- (void)connectAndLaunch:(BOOL)launch restartHost:(BOOL)restart {
  if (_busy || ![self checkName]) return;
  const std::string role = Bytes(_role), endpoint = Bytes(_endpoint), name = Bytes(_name.text);
  const auto docs = _docs;
  const NSUInteger generation = ++_generation;
  _busy = YES; _ready = NO; _name.enabled = NO;
  _status = [NSString stringWithFormat:@"%@…", role == "host" ? @"Starting your lobby" : @"Checking connection to the host"];
  nfsmw::boot::Trace("[lan-setup] " + role + " endpoint=" + endpoint + " launch=" + (launch ? "yes" : "no"));
  [self refresh];
  dispatch_async(SetupQueue(), ^{
    if (restart) nfsmw::servidor::Parar();
    const auto prepared = nfsmw::lan::Prepare(role, endpoint, name, docs);
    dispatch_async(dispatch_get_main_queue(), ^{
      if (self->_closing || generation != self->_generation) return;
      self->_busy = NO; self->_name.enabled = YES;
      if (!prepared.error.empty()) {
        self->_status = Text(prepared.error);
        nfsmw::boot::Trace("[lan-setup] connection failed: " + prepared.error);
      } else {
        self->_ready = YES; self->_endpoint = Text(prepared.ip); self->_preparedName = self->_name.text;
        self->_settings[@"lan_resolved_ip"] = self->_endpoint;
        self->_settings[@"lan_server"] = self->_endpoint;
        self->_status = prepared.hosting
          ? [NSString stringWithFormat:@"Hosting as %@\nAddress: %@\n\nOn the other device, tap Join and select %@. Keep this app open.", self->_name.text,self->_endpoint,self->_name.text]
          : [NSString stringWithFormat:@"Connected to %@\nAddress: %@\n\nYou are using the OTHER device’s lobby. You do not need to host here.", self->_serverName,self->_endpoint];
        nfsmw::launcher::WriteSettings(self->_docs, self->_settings);
        nfsmw::boot::Trace("[lan-setup] ready " + role + " server=" + prepared.ip);
        if (launch) {
          self->_settings[@"lan_mode"] = self->_role;
          nfsmw::launcher::WriteSettings(self->_docs, self->_settings);
          self->_launching = YES; [self->_timer invalidate];
          self->_launch(); return;
        }
      }
      [self refresh];
    });
  });
}

- (NSInteger)numberOfSectionsInTableView:(UITableView*)tableView { return 5; }
- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  if (section == 0 || section == 2) return 1;
  if (section == 1) return 2;
  if (section == 3) return [_role isEqualToString:@"join"] ? NSInteger(_hosts.size()) + 2 : 0;
  return _ready ? 1 : 0;
}
- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  if (section == 0) return @"Your player name";
  if (section == 1) return @"Choose how to play";
  if (section == 2) return @"Connection";
  if (section == 3 && [_role isEqualToString:@"join"]) return @"Nearby hosts";
  return nil;
}
- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  if (section == 0) return @"Each device needs a different name. Your single-player saves keep their existing identity.";
  if (section == 1) return @"Choose Host on ONE device and Join on the others. iPhone, iPad and Android can use the same lobby.";
  if (section == 4 && _ready) return [_role isEqualToString:@"host"]
    ? @"After launching: Xbox Live → Quick Match → Create Game. Create the race on this device; the other player then joins it. Hosting the lobby alone does not create a race."
    : @"After launching: Xbox Live → Quick Match. Find and join the race created by the host. Do not create a second race here.";
  return nil;
}
- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleSubtitle reuseIdentifier:nil];
  cell.textLabel.numberOfLines = 0; cell.detailTextLabel.numberOfLines = 0;
  if (ip.section == 0) {
    cell.textLabel.text = @"Name"; cell.accessoryView = _name; cell.selectionStyle = UITableViewCellSelectionStyleNone;
  } else if (ip.section == 1) {
    NSString* role = ip.row == 0 ? @"host" : @"join";
    cell.textLabel.text = ip.row == 0 ? @"Host a game" : @"Join a game";
    cell.detailTextLabel.text = ip.row == 0 ? @"Start a lobby on this device" : @"Find a lobby on another device";
    cell.imageView.image = [UIImage systemImageNamed:ip.row == 0 ? @"wifi" : @"magnifyingglass"];
    cell.accessoryType = [_role isEqualToString:role] ? UITableViewCellAccessoryCheckmark : UITableViewCellAccessoryNone;
  } else if (ip.section == 2) {
    cell.textLabel.text = _status; cell.selectionStyle = UITableViewCellSelectionStyleNone;
    if (_busy) {
      UIActivityIndicatorView* spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleMedium];
      [spinner startAnimating]; cell.accessoryView = spinner;
    }
  } else if (ip.section == 3) {
    if (size_t(ip.row) < _hosts.size()) {
      const auto& h = _hosts[size_t(ip.row)];
      cell.textLabel.text = Text(h.nombre);
      cell.detailTextLabel.text = [NSString stringWithFormat:@"%@ · %d in-game players", Text(h.ip), h.jugadores];
      cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
    } else cell.textLabel.text = size_t(ip.row) == _hosts.size() ? @"Search again" : @"Enter address manually…";
  } else {
    cell.textLabel.text = @"Launch multiplayer"; cell.textLabel.textColor = UIColor.systemGreenColor;
    cell.imageView.image = [UIImage systemImageNamed:@"play.fill"];
  }
  if (_busy && ip.section != 2) cell.contentView.alpha = 0.45;
  return cell;
}
- (void)tableView:(UITableView*)tableView didSelectRowAtIndexPath:(NSIndexPath*)ip {
  [tableView deselectRowAtIndexPath:ip animated:YES];
  if (_busy) return;
  if (ip.section == 1) { ip.row == 0 ? [self chooseHost] : [self search]; return; }
  if (ip.section == 3) {
    if (size_t(ip.row) < _hosts.size()) {
      _endpoint = Text(_hosts[size_t(ip.row)].ip); _serverName = Text(_hosts[size_t(ip.row)].nombre);
      [self connectAndLaunch:NO restartHost:NO];
    } else if (size_t(ip.row) == _hosts.size()) [self search];
    else [self manualAddress];
  }
  if (ip.section == 4 && _ready) [self connectAndLaunch:YES restartHost:NO];
}
@end

namespace nfsmw::lan {
UIViewController* MakeSetup(const std::filesystem::path& docs,
                           NSMutableDictionary<NSString*, NSString*>* settings,
                           std::function<void()> launch) {
  return [[NFSLanSetupController alloc] initWithDocuments:docs settings:settings launch:std::move(launch)];
}
}
