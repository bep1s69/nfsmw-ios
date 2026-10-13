// NFSMW Recompiled - the save manager (see save_manager.h).
//
// The game's saves are content packages the SDK keeps as plain folders:
//   Documents/data/<xuid>/<title id>/00000001/<NAME>/<NAME>   the save (MC02)
//   Documents/data/<xuid>/<title id>/Headers/00000001/<NAME>.header
// A save here is that pair, named <xuid>_<title>_<NAME> (its id).
//
// Backups: Documents/SaveBackups/<id>/<yyyy-MM-dd HH.mm.ss>/ (the folder and
// the header), the newest 10 kept: one is made whenever a save changed since
// its last backup (at launcher start), and before any restore or download
// replaces it.
//
// iCloud: Apple's iCloud containers need a paid developer certificate, so not
// for a sideloaded app. Instead the player picks a folder in iCloud Drive
// (Files); the app keeps a bookmark to it and copies saves to
// <folder>/NFSMW Saves/<id>/ with info.plist (content hash, date, device).
// The hash of each save as last synced is remembered here, which tells who
// changed since: this device, iCloud, or both (a conflict, resolved by the
// player).

#import <UIKit/UIKit.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

#include <algorithm>
#include <cstring>
#include <chrono>
#include <ctime>
#include <string>
#include <system_error>
#include <vector>

#include "save_manager.h"

namespace fs = std::filesystem;

namespace {

NSString* const kCloudBookmark = @"nfsmw.saves.cloudBookmark";
NSString* const kSyncedHashes = @"nfsmw.saves.synced";
constexpr size_t kBackupsKept = 10;

struct Save {
  std::string id;    // <xuid>_<title>_<NAME>
  std::string name;  // NAME
  fs::path root;     // Documents/data/<xuid>/<title>
  uint64_t hash = 0;
  std::time_t modified = 0;
  uintmax_t bytes = 0;
  fs::path Dir() const { return root / "00000001" / name; }
  fs::path Header() const { return root / "Headers" / "00000001" / (name + ".header"); }
};

bool IsHex(const std::string& s, size_t n) {
  return s.size() == n && std::all_of(s.begin(), s.end(), [](char c) { return std::isxdigit(uint8_t(c)); });
}

std::time_t ToTimeT(fs::file_time_type t) {
  using namespace std::chrono;
  return system_clock::to_time_t(time_point_cast<system_clock::duration>(t - fs::file_time_type::clock::now() +
                                                                          system_clock::now()));
}

// FNV-1a over the files' relative paths and bytes, in name order.
void HashInto(uint64_t& h, const void* data, size_t n) {
  const auto* p = static_cast<const uint8_t*>(data);
  for (size_t i = 0; i < n; ++i) h = (h ^ p[i]) * 0x100000001B3ull;
}

void Measure(Save& s) {
  std::error_code ec;
  std::vector<fs::path> files;
  if (fs::is_directory(s.Dir(), ec)) {
    for (auto& e : fs::recursive_directory_iterator(s.Dir(), ec)) {
      if (e.is_regular_file(ec)) files.push_back(e.path());
    }
  }
  if (fs::exists(s.Header(), ec)) files.push_back(s.Header());
  std::sort(files.begin(), files.end());
  uint64_t h = 0xCBF29CE484222325ull;
  s.bytes = 0;
  s.modified = 0;
  for (const fs::path& f : files) {
    const std::string rel = f.lexically_relative(s.root).generic_string();
    HashInto(h, rel.data(), rel.size());
    NSData* d = [NSData dataWithContentsOfFile:@(f.c_str())];
    HashInto(h, d.bytes, d.length);
    s.bytes += d.length;
    s.modified = std::max(s.modified, ToTimeT(fs::last_write_time(f, ec)));
  }
  s.hash = h;
}

std::vector<Save> FindSaves(const fs::path& docs) {
  std::vector<Save> out;
  std::error_code ec;
  const fs::path data = docs / "data";
  for (auto& x : fs::directory_iterator(data, ec)) {
    if (!x.is_directory(ec) || !IsHex(x.path().filename().string(), 16)) continue;
    for (auto& t : fs::directory_iterator(x.path(), ec)) {
      if (!t.is_directory(ec) || !IsHex(t.path().filename().string(), 8)) continue;
      for (auto& p : fs::directory_iterator(t.path() / "00000001", ec)) {
        if (!p.is_directory(ec)) continue;
        Save s;
        s.root = t.path();
        s.name = p.path().filename().string();
        s.id = x.path().filename().string() + "_" + t.path().filename().string() + "_" + s.name;
        Measure(s);
        out.push_back(s);
      }
    }
  }
  std::sort(out.begin(), out.end(), [](const Save& a, const Save& b) { return a.modified > b.modified; });
  return out;
}

// Where a save with this id lives (new ones: the first profile found, or the
// emulator's default one).
fs::path RootFor(const fs::path& docs, const std::string& id) {
  const size_t a = id.find('_'), b = id.find('_', a + 1);
  if (a == std::string::npos || b == std::string::npos) return {};
  return docs / "data" / id.substr(0, a) / id.substr(a + 1, b - a - 1);
}

std::string NameOf(const std::string& id) {
  const size_t a = id.find('_'), b = id.find('_', a + 1);
  return b == std::string::npos ? id : id.substr(b + 1);
}

// The pair (folder + header) copied from one layout to another, replacing.
//   from_dir/from_header -> to_dir/to_header
bool CopyPair(const fs::path& from_dir, const fs::path& from_header, const fs::path& to_dir,
              const fs::path& to_header) {
  std::error_code ec;
  fs::remove_all(to_dir, ec);
  fs::create_directories(to_dir.parent_path(), ec);
  fs::copy(from_dir, to_dir, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
  if (ec) return false;
  if (fs::exists(from_header)) {
    fs::create_directories(to_header.parent_path(), ec);
    fs::copy_file(from_header, to_header, fs::copy_options::overwrite_existing, ec);
  }
  return !ec;
}

// --- Backups -------------------------------------------------------------------

fs::path BackupsOf(const fs::path& docs, const std::string& id) { return docs / "SaveBackups" / id; }

std::vector<fs::path> ListBackups(const fs::path& docs, const std::string& id) {
  std::vector<fs::path> out;
  std::error_code ec;
  for (auto& e : fs::directory_iterator(BackupsOf(docs, id), ec)) {
    if (e.is_directory(ec)) out.push_back(e.path());
  }
  std::sort(out.rbegin(), out.rend());  // newest first (the names are timestamps)
  return out;
}

std::string Stamp() {
  const std::time_t now = std::time(nullptr);
  char buf[32];
  std::strftime(buf, sizeof(buf), "%Y-%m-%d %H.%M.%S", std::localtime(&now));
  return buf;
}

uint64_t ReadHashFile(const fs::path& p) {
  NSString* s = [NSString stringWithContentsOfFile:@(p.c_str()) encoding:NSUTF8StringEncoding error:nil];
  return s ? strtoull(s.UTF8String, nullptr, 16) : 0;
}

void WriteHashFile(const fs::path& p, uint64_t h) {
  [[NSString stringWithFormat:@"%016llx", (unsigned long long)h] writeToFile:@(p.c_str())
                                                                 atomically:YES
                                                                   encoding:NSUTF8StringEncoding
                                                                      error:nil];
}

// A backup of the save unless the newest one already holds the same content.
bool Backup(const fs::path& docs, const Save& s, bool force = false) {
  const auto existing = ListBackups(docs, s.id);
  if (!force && !existing.empty() && ReadHashFile(existing.front() / "hash.txt") == s.hash) return false;
  const fs::path dest = BackupsOf(docs, s.id) / Stamp();
  if (!CopyPair(s.Dir(), s.Header(), dest / s.name, dest / (s.name + ".header"))) return false;
  WriteHashFile(dest / "hash.txt", s.hash);
  std::error_code ec;
  auto all = ListBackups(docs, s.id);
  for (size_t i = kBackupsKept; i < all.size(); ++i) fs::remove_all(all[i], ec);
  return true;
}

bool RestoreBackup(const fs::path& docs, const Save& s, const fs::path& backup) {
  Backup(docs, s);  // what is replaced is kept too
  return CopyPair(backup / s.name, backup / (s.name + ".header"), s.Dir(), s.Header());
}

// --- iCloud Drive folder -------------------------------------------------------

// The chosen folder (security-scoped: access started; stop with StopCloud).
NSURL* StartCloud() {
  NSData* bookmark = [NSUserDefaults.standardUserDefaults dataForKey:kCloudBookmark];
  if (!bookmark) return nil;
  BOOL stale = NO;
  NSURL* url = [NSURL URLByResolvingBookmarkData:bookmark options:0 relativeToURL:nil bookmarkDataIsStale:&stale
                                           error:nil];
  if (!url || ![url startAccessingSecurityScopedResource]) return nil;
  if (stale) {
    NSData* fresh = [url bookmarkDataWithOptions:0 includingResourceValuesForKeys:nil relativeToURL:nil error:nil];
    if (fresh) [NSUserDefaults.standardUserDefaults setObject:fresh forKey:kCloudBookmark];
  }
  return url;
}

void StopCloud(NSURL* url) { [url stopAccessingSecurityScopedResource]; }

fs::path CloudSaves(NSURL* cloud) { return fs::path(cloud.path.UTF8String) / "NFSMW Saves"; }

struct CloudInfo {
  bool present = false;
  uint64_t hash = 0;
  NSDate* modified = nil;
  NSString* device = nil;
};

CloudInfo ReadCloudInfo(NSURL* cloud, const std::string& id) {
  CloudInfo out;
  const fs::path info = CloudSaves(cloud) / id / "info.plist";
  __block NSDictionary* d = nil;
  NSFileCoordinator* fc = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
  [fc coordinateReadingItemAtURL:[NSURL fileURLWithPath:@(info.c_str())]
                         options:0
                           error:nil
                      byAccessor:^(NSURL* u) {
                        d = [NSDictionary dictionaryWithContentsOfURL:u];
                      }];
  if (!d) return out;
  out.present = true;
  out.hash = strtoull([d[@"hash"] UTF8String] ?: "0", nullptr, 16);
  out.modified = d[@"modified"];
  out.device = d[@"device"];
  return out;
}

std::vector<std::string> CloudIds(NSURL* cloud) {
  std::vector<std::string> out;
  std::error_code ec;
  for (auto& e : fs::directory_iterator(CloudSaves(cloud), ec)) {
    if (e.is_directory(ec)) out.push_back(e.path().filename().string());
  }
  return out;
}

uint64_t SyncedHash(const std::string& id) {
  NSString* v = [NSUserDefaults.standardUserDefaults dictionaryForKey:kSyncedHashes][@(id.c_str())];
  return v ? strtoull(v.UTF8String, nullptr, 16) : 0;
}

void SetSyncedHash(const std::string& id, uint64_t h) {
  NSMutableDictionary* d = [[NSUserDefaults.standardUserDefaults dictionaryForKey:kSyncedHashes] mutableCopy]
                               ?: [NSMutableDictionary dictionary];
  d[@(id.c_str())] = [NSString stringWithFormat:@"%016llx", (unsigned long long)h];
  [NSUserDefaults.standardUserDefaults setObject:d forKey:kSyncedHashes];
}

bool Upload(NSURL* cloud, const Save& s) {
  const fs::path dest = CloudSaves(cloud) / s.id;
  __block bool ok = false;
  NSFileCoordinator* fc = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
  [fc coordinateWritingItemAtURL:[NSURL fileURLWithPath:@(dest.c_str())]
                         options:NSFileCoordinatorWritingForReplacing
                           error:nil
                      byAccessor:^(NSURL*) {
                        ok = CopyPair(s.Dir(), s.Header(), dest / s.name, dest / (s.name + ".header"));
                        NSDictionary* info = @{
                          @"hash" : [NSString stringWithFormat:@"%016llx", (unsigned long long)s.hash],
                          @"modified" : [NSDate dateWithTimeIntervalSince1970:s.modified],
                          @"device" : UIDevice.currentDevice.name ?: @"?",
                        };
                        ok = ok && [info writeToFile:@((dest / "info.plist").c_str()) atomically:YES];
                      }];
  if (ok) SetSyncedHash(s.id, s.hash);
  return ok;
}

bool Download(const fs::path& docs, NSURL* cloud, const std::string& id) {
  const fs::path src = CloudSaves(cloud) / id;
  const std::string name = NameOf(id);
  Save local;
  local.id = id;
  local.name = name;
  local.root = RootFor(docs, id);
  std::error_code ec;
  if (fs::exists(local.Dir(), ec)) {
    Measure(local);
    Backup(docs, local);  // what is replaced is kept
  }
  __block bool ok = false;
  NSFileCoordinator* fc = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
  [fc coordinateReadingItemAtURL:[NSURL fileURLWithPath:@(src.c_str())]
                         options:0
                           error:nil
                      byAccessor:^(NSURL*) {
                        ok = CopyPair(src / name, src / (name + ".header"), local.Dir(), local.Header());
                      }];
  if (ok) {
    Measure(local);
    SetSyncedHash(id, local.hash);
  }
  return ok;
}

enum class Sync { kNoCloud, kInSync, kLocalNewer, kCloudNewer, kConflict, kLocalOnly, kCloudOnly };

Sync StateOf(const Save* local, const CloudInfo& c, uint64_t synced) {
  if (!local) return Sync::kCloudOnly;
  if (!c.present) return Sync::kLocalOnly;
  if (local->hash == c.hash) return Sync::kInSync;
  if (c.hash == synced) return Sync::kLocalNewer;
  if (local->hash == synced) return Sync::kCloudNewer;
  return Sync::kConflict;
}

NSString* SyncText(Sync s) {
  switch (s) {
    case Sync::kNoCloud: return @"";
    case Sync::kInSync: return @"In sync with iCloud";
    case Sync::kLocalNewer: return @"Newer on this device";
    case Sync::kCloudNewer: return @"Newer in iCloud";
    case Sync::kConflict: return @"Changed here and in iCloud";
    case Sync::kLocalOnly: return @"Not in iCloud yet";
    case Sync::kCloudOnly: return @"Only in iCloud";
  }
  return @"";
}

UIColor* SyncColor(Sync s) {
  switch (s) {
    case Sync::kInSync: return UIColor.systemGreenColor;
    case Sync::kCloudNewer:
    case Sync::kCloudOnly: return UIColor.systemBlueColor;
    case Sync::kConflict: return UIColor.systemOrangeColor;
    default: return UIColor.secondaryLabelColor;
  }
}

NSString* DateText(std::time_t t) {
  if (!t) return @"?";
  return [NSDateFormatter localizedStringFromDate:[NSDate dateWithTimeIntervalSince1970:t]
                                        dateStyle:NSDateFormatterMediumStyle
                                        timeStyle:NSDateFormatterShortStyle];
}

// The career's progress, read from the save (MC02, big-endian, the same
// format as the PC game's). Found by comparing two saves of the same career:
//  - cash: a u32 at 0x4039 (24,700, then 200 after buying a car);
//  - bounty: a float in a list of keyed records whose order changes between
//    saves, right after the key bytes 1C B2 90 8B E4 E2 55 47 33 00 31.
// Shown only when the values look sane, so a save laid out differently shows
// nothing rather than nonsense.
NSString* Progress(const Save& s) {
  NSData* d = [NSData dataWithContentsOfFile:@((s.Dir() / s.name).c_str())];
  const auto* p = static_cast<const uint8_t*>(d.bytes);
  if (d.length < 0x4040 || std::memcmp(p, "MC02", 4) != 0) return nil;
  auto u32 = [&](size_t at) {
    return uint32_t(p[at]) << 24 | uint32_t(p[at + 1]) << 16 | uint32_t(p[at + 2]) << 8 | uint32_t(p[at + 3]);
  };
  NSNumberFormatter* f = [NSNumberFormatter new];
  f.numberStyle = NSNumberFormatterDecimalStyle;
  NSMutableArray* parts = [NSMutableArray array];
  const uint32_t cash = u32(0x4039);
  if (cash <= 100000000u) [parts addObject:[NSString stringWithFormat:@"Cash $%@", [f stringFromNumber:@(cash)]]];
  static const uint8_t kBountyKey[] = {0x1C, 0xB2, 0x90, 0x8B, 0xE4, 0xE2, 0x55, 0x47, 0x33, 0x00, 0x31};
  const size_t search_end = std::min<size_t>(d.length, 0x1000);
  for (size_t i = 0; i + sizeof(kBountyKey) + 4 <= search_end; ++i) {
    if (std::memcmp(p + i, kBountyKey, sizeof(kBountyKey)) != 0) continue;
    const uint32_t bits = u32(i + sizeof(kBountyKey));
    float bounty;
    std::memcpy(&bounty, &bits, 4);
    if (bounty >= 0.0f && bounty < 1.0e8f) {
      [parts addObject:[NSString stringWithFormat:@"Bounty %@", [f stringFromNumber:@(uint64_t(bounty))]]];
    }
    break;
  }
  return parts.count ? [parts componentsJoinedByString:@" · "] : nil;
}

}  // namespace

// ---------------------------------------------------------------------------
//  The screen
// ---------------------------------------------------------------------------
@interface NFSSaveManagerController : UITableViewController <UIDocumentPickerDelegate>
- (instancetype)initWithDocuments:(fs::path)docs;
@end

@implementation NFSSaveManagerController {
  fs::path _docs;
  std::vector<Save> _saves;
  std::vector<std::string> _cloudOnly;
  std::vector<Sync> _state;  // per _saves
  NSString* _cloudName;      // the folder's name, nil without one
  BOOL _pickingCloud;        // the document picker: the iCloud folder (else an import)
}

- (instancetype)initWithDocuments:(fs::path)docs {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _docs = docs;
    self.title = @"Saves";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  [self reload];
}

- (void)reload {
  _saves = FindSaves(_docs);
  _state.assign(_saves.size(), Sync::kNoCloud);
  _cloudOnly.clear();
  _cloudName = nil;
  if (NSURL* cloud = StartCloud()) {
    _cloudName = cloud.lastPathComponent;
    for (size_t i = 0; i < _saves.size(); ++i) {
      _state[i] = StateOf(&_saves[i], ReadCloudInfo(cloud, _saves[i].id), SyncedHash(_saves[i].id));
    }
    for (const std::string& id : CloudIds(cloud)) {
      if (std::none_of(_saves.begin(), _saves.end(), [&](const Save& s) { return s.id == id; })) {
        _cloudOnly.push_back(id);
      }
    }
    StopCloud(cloud);
  }
  [self.tableView reloadData];
}

// 0: iCloud Drive, 1: saves on this device, 2: only in iCloud, 3: import.
- (NSInteger)numberOfSectionsInTableView:(UITableView*)tableView {
  return 4;
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  switch (section) {
    case 0: return _cloudName ? 2 : 1;
    case 1: return std::max<NSInteger>(1, NSInteger(_saves.size()));
    case 2: return NSInteger(_cloudOnly.size());
    default: return 1;
  }
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  switch (section) {
    case 0: return @"iCloud Drive";
    case 1: return @"On this device";
    case 2: return _cloudOnly.empty() ? nil : @"Only in iCloud";
    default: return nil;
  }
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  if (section == 0) {
    return @"Saves are copied to \"NFSMW Saves\" in this folder. Pick the same folder on your other "
           @"devices to carry a career between them. Changes made only on this device are copied "
           @"automatically when the launcher opens; anything newer in iCloud waits for you.";
  }
  if (section == 1) {
    return @"Tap a save for backups, iCloud, export and delete. A backup is made automatically "
           @"whenever a save changed (the newest 10 are kept).";
  }
  return nil;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault reuseIdentifier:nil];
  UIListContentConfiguration* c = UIListContentConfiguration.subtitleCellConfiguration;
  c.secondaryTextProperties.color = UIColor.secondaryLabelColor;
  c.secondaryTextProperties.numberOfLines = 0;
  if (ip.section == 0) {
    if (ip.row == 0) {
      c.image = [UIImage systemImageNamed:@"icloud"];
      c.text = _cloudName ? _cloudName : @"Choose an iCloud Drive folder…";
      c.secondaryText = _cloudName ? @"Tap to choose another folder" : nil;
    } else {
      c.image = [UIImage systemImageNamed:@"arrow.triangle.2.circlepath"];
      c.text = @"Sync now";
      c.secondaryText = @"Copies what changed only on this device to iCloud";
    }
    cell.accessoryType = UITableViewCellAccessoryNone;
  } else if (ip.section == 1) {
    if (_saves.empty()) {
      c.text = @"No saves yet";
      c.secondaryText = @"Start a career in the game: its save appears here.";
      cell.selectionStyle = UITableViewCellSelectionStyleNone;
    } else {
      const Save& s = _saves[size_t(ip.row)];
      c.image = [UIImage systemImageNamed:@"flag.checkered"];
      c.text = @(s.name.c_str());
      NSMutableArray* lines = [NSMutableArray array];
      if (NSString* p = Progress(s)) [lines addObject:p];
      [lines addObject:[NSString stringWithFormat:@"Saved %@ · %llu KB", DateText(s.modified),
                                                  (unsigned long long)(s.bytes + 1023) / 1024]];
      c.secondaryText = [lines componentsJoinedByString:@"\n"];
      if (_state[size_t(ip.row)] != Sync::kNoCloud) {
        UILabel* badge = [[UILabel alloc] init];
        badge.text = SyncText(_state[size_t(ip.row)]);
        badge.font = [UIFont systemFontOfSize:12 weight:UIFontWeightSemibold];
        badge.textColor = SyncColor(_state[size_t(ip.row)]);
        [badge sizeToFit];
        cell.accessoryView = badge;
      } else {
        cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
      }
    }
  } else if (ip.section == 2) {
    c.image = [UIImage systemImageNamed:@"icloud.and.arrow.down"];
    c.text = @(NameOf(_cloudOnly[size_t(ip.row)]).c_str());
    c.secondaryText = @"Tap to download it to this device";
  } else {
    c.image = [UIImage systemImageNamed:@"square.and.arrow.down"];
    c.text = @"Import a save…";
    c.secondaryText = @"A save folder exported from this app (unzip it in Files first).";
  }
  cell.contentConfiguration = c;
  return cell;
}

- (void)alert:(NSString*)title message:(NSString*)message {
  UIAlertController* a = [UIAlertController alertControllerWithTitle:title message:message
                                                      preferredStyle:UIAlertControllerStyleAlert];
  [a addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
  [self presentViewController:a animated:YES completion:nil];
}

- (void)pickFolder:(BOOL)cloud {
  _pickingCloud = cloud;
  UIDocumentPickerViewController* p =
      [[UIDocumentPickerViewController alloc] initForOpeningContentTypes:@[ UTTypeFolder ]];
  p.delegate = self;
  [self presentViewController:p animated:YES completion:nil];
}

- (void)documentPicker:(UIDocumentPickerViewController*)picker didPickDocumentsAtURLs:(NSArray<NSURL*>*)urls {
  NSURL* url = urls.firstObject;
  if (!url) return;
  if (_pickingCloud) {
    [url startAccessingSecurityScopedResource];
    NSData* bookmark = [url bookmarkDataWithOptions:0 includingResourceValuesForKeys:nil relativeToURL:nil error:nil];
    [url stopAccessingSecurityScopedResource];
    if (bookmark) {
      [NSUserDefaults.standardUserDefaults setObject:bookmark forKey:kCloudBookmark];
      nfsmw::saves::AutoSync(_docs);
    }
    [self reload];
    return;
  }
  // Import: a folder holding <NAME>/<NAME> (and <NAME>.header), as exported,
  // or the save folder <NAME> itself.
  [url startAccessingSecurityScopedResource];
  fs::path dir(url.path.UTF8String);
  std::error_code ec;
  std::string name = dir.filename().string();
  fs::path save_dir = dir, header = dir.parent_path() / (name + ".header");
  if (!fs::is_regular_file(dir / name, ec)) {
    // An export: the one sub-folder with a same-named file inside.
    for (auto& e : fs::directory_iterator(dir, ec)) {
      const std::string n = e.path().filename().string();
      if (e.is_directory(ec) && fs::is_regular_file(e.path() / n, ec)) {
        name = n;
        save_dir = e.path();
        header = dir / (n + ".header");
        break;
      }
    }
  }
  bool ok = fs::is_regular_file(save_dir / name, ec);
  if (ok) {
    Save target;
    target.name = name;
    target.root = _saves.empty() ? _docs / "data" / "B13EBABEBABEBABE" / "454107D9" : _saves.front().root;
    target.id = target.root.parent_path().filename().string() + "_" + target.root.filename().string() + "_" + name;
    if (fs::exists(target.Dir(), ec)) {
      Measure(target);
      Backup(_docs, target);
    }
    ok = CopyPair(save_dir, header, target.Dir(), target.Header());
  }
  [url stopAccessingSecurityScopedResource];
  [self reload];
  [self alert:ok ? @"Imported" : @"Not a save"
      message:ok ? [NSString stringWithFormat:@"%s is on this device now.", name.c_str()]
                 : @"Choose the folder you exported (unzipped in Files), or the save's own folder."];
}

- (void)exportSave:(const Save&)s from:(UIView*)source {
  // A folder <NAME>/ with the save and its header, zipped by the system.
  NSString* tmp = [NSTemporaryDirectory() stringByAppendingPathComponent:@(s.name.c_str())];
  fs::path out(tmp.UTF8String);
  std::error_code ec;
  fs::remove_all(out, ec);
  CopyPair(s.Dir(), s.Header(), out / s.name, out / (s.name + ".header"));
  __block NSURL* zip = nil;
  NSFileCoordinator* fc = [[NSFileCoordinator alloc] initWithFilePresenter:nil];
  [fc coordinateReadingItemAtURL:[NSURL fileURLWithPath:tmp]
                         options:NSFileCoordinatorReadingForUploading
                           error:nil
                      byAccessor:^(NSURL* u) {
                        NSString* dest = [NSTemporaryDirectory()
                            stringByAppendingPathComponent:[NSString stringWithFormat:@"%s save.zip", s.name.c_str()]];
                        [NSFileManager.defaultManager removeItemAtPath:dest error:nil];
                        if ([NSFileManager.defaultManager copyItemAtURL:u toURL:[NSURL fileURLWithPath:dest] error:nil]) {
                          zip = [NSURL fileURLWithPath:dest];
                        }
                      }];
  if (!zip) {
    [self alert:@"Export failed" message:nil];
    return;
  }
  UIActivityViewController* share = [[UIActivityViewController alloc] initWithActivityItems:@[ zip ]
                                                                      applicationActivities:nil];
  share.popoverPresentationController.sourceView = source;
  share.popoverPresentationController.sourceRect = source.bounds;
  [self presentViewController:share animated:YES completion:nil];
}

- (void)chooseBackupFor:(const Save&)s {
  const auto backups = ListBackups(_docs, s.id);
  UIAlertController* sheet = [UIAlertController alertControllerWithTitle:@"Restore a backup"
                                                                 message:backups.empty() ? @"No backups yet." : nil
                                                          preferredStyle:UIAlertControllerStyleAlert];
  const Save copy = s;
  for (const fs::path& b : backups) {
    NSString* title = @(b.filename().c_str());
    [sheet addAction:[UIAlertAction actionWithTitle:title
                                              style:UIAlertActionStyleDefault
                                            handler:^(UIAlertAction*) {
                                              const bool ok = RestoreBackup(self->_docs, copy, b);
                                              [self reload];
                                              [self alert:ok ? @"Restored" : @"Restore failed"
                                                  message:ok ? @"The save you had is kept as a backup too." : nil];
                                            }]];
  }
  [sheet addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  [self presentViewController:sheet animated:YES completion:nil];
}

- (void)actionsFor:(size_t)i from:(UIView*)source {
  const Save s = _saves[i];
  const Sync state = _state[i];
  UIAlertController* sheet =
      [UIAlertController alertControllerWithTitle:@(s.name.c_str())
                                          message:state == Sync::kNoCloud ? nil : SyncText(state)
                                   preferredStyle:UIAlertControllerStyleActionSheet];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Back up now"
                                            style:UIAlertActionStyleDefault
                                          handler:^(UIAlertAction*) {
                                            Backup(self->_docs, s, true);
                                            [self alert:@"Backed up" message:nil];
                                          }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Restore a backup…"
                                            style:UIAlertActionStyleDefault
                                          handler:^(UIAlertAction*) {
                                            [self chooseBackupFor:s];
                                          }]];
  if (state != Sync::kNoCloud) {
    [sheet addAction:[UIAlertAction actionWithTitle:@"Copy this device's save to iCloud"
                                              style:state == Sync::kCloudNewer || state == Sync::kConflict
                                                        ? UIAlertActionStyleDestructive
                                                        : UIAlertActionStyleDefault
                                            handler:^(UIAlertAction*) {
                                              NSURL* cloud = StartCloud();
                                              const bool ok = cloud && Upload(cloud, s);
                                              StopCloud(cloud);
                                              [self reload];
                                              if (!ok) [self alert:@"Upload failed" message:nil];
                                            }]];
  }
  if (state == Sync::kCloudNewer || state == Sync::kConflict || state == Sync::kInSync ||
      state == Sync::kLocalNewer) {
    [sheet addAction:[UIAlertAction actionWithTitle:@"Use the iCloud save here"
                                              style:state == Sync::kLocalNewer || state == Sync::kConflict
                                                        ? UIAlertActionStyleDestructive
                                                        : UIAlertActionStyleDefault
                                            handler:^(UIAlertAction*) {
                                              NSURL* cloud = StartCloud();
                                              const bool ok = cloud && Download(self->_docs, cloud, s.id);
                                              StopCloud(cloud);
                                              [self reload];
                                              [self alert:ok ? @"Done" : @"Download failed"
                                                  message:ok ? @"This device's save is kept as a backup." : nil];
                                            }]];
  }
  [sheet addAction:[UIAlertAction actionWithTitle:@"Export…"
                                            style:UIAlertActionStyleDefault
                                          handler:^(UIAlertAction*) {
                                            [self exportSave:s from:source];
                                          }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Delete…"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) {
                                            [self confirmDelete:s];
                                          }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  sheet.popoverPresentationController.sourceView = source;
  sheet.popoverPresentationController.sourceRect = source.bounds;
  [self presentViewController:sheet animated:YES completion:nil];
}

- (void)confirmDelete:(const Save&)s {
  const Save copy = s;
  UIAlertController* a = [UIAlertController
      alertControllerWithTitle:[NSString stringWithFormat:@"Delete %s?", s.name.c_str()]
                       message:@"It is backed up first, so it can still be restored from Restore a backup "
                               @"(after importing or recreating it). The iCloud copy is not touched."
                preferredStyle:UIAlertControllerStyleAlert];
  [a addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  [a addAction:[UIAlertAction actionWithTitle:@"Delete"
                                        style:UIAlertActionStyleDestructive
                                      handler:^(UIAlertAction*) {
                                        Backup(self->_docs, copy, true);
                                        std::error_code ec;
                                        fs::remove_all(copy.Dir(), ec);
                                        fs::remove(copy.Header(), ec);
                                        [self reload];
                                      }]];
  [self presentViewController:a animated:YES completion:nil];
}

- (void)tableView:(UITableView*)tableView didSelectRowAtIndexPath:(NSIndexPath*)ip {
  [tableView deselectRowAtIndexPath:ip animated:YES];
  UIView* source = [tableView cellForRowAtIndexPath:ip] ?: tableView;
  if (ip.section == 0) {
    if (ip.row == 0) {
      [self pickFolder:YES];
    } else {
      const int attention = nfsmw::saves::AutoSync(_docs);
      [self reload];
      [self alert:@"Synced"
          message:attention ? [NSString stringWithFormat:@"%d save(s) are newer in iCloud or changed on both "
                                                         @"sides: tap them to choose.",
                                                         attention]
                            : @"Everything changed on this device is in iCloud."];
    }
  } else if (ip.section == 1) {
    if (!_saves.empty()) [self actionsFor:size_t(ip.row) from:source];
  } else if (ip.section == 2) {
    const std::string id = _cloudOnly[size_t(ip.row)];
    NSURL* cloud = StartCloud();
    const bool ok = cloud && Download(_docs, cloud, id);
    StopCloud(cloud);
    [self reload];
    if (!ok) [self alert:@"Download failed" message:nil];
  } else {
    [self pickFolder:NO];
  }
}

@end

namespace nfsmw::saves {

UIViewController* MakeSaveManager(const fs::path& documents) {
  return [[NFSSaveManagerController alloc] initWithDocuments:documents];
}

int AutoSync(const fs::path& documents) {
  int attention = 0;
  const auto saves = FindSaves(documents);
  for (const Save& s : saves) Backup(documents, s);
  NSURL* cloud = StartCloud();
  if (!cloud) return 0;
  for (const Save& s : saves) {
    const Sync state = StateOf(&s, ReadCloudInfo(cloud, s.id), SyncedHash(s.id));
    if (state == Sync::kLocalNewer || state == Sync::kLocalOnly) {
      Upload(cloud, s);
    } else if (state == Sync::kCloudNewer || state == Sync::kConflict) {
      ++attention;
    }
  }
  for (const std::string& id : CloudIds(cloud)) {
    if (std::none_of(saves.begin(), saves.end(), [&](const Save& s) { return s.id == id; })) ++attention;
  }
  StopCloud(cloud);
  return attention;
}

}  // namespace nfsmw::saves
