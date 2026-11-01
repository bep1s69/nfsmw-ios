// Read-only TCP path diagnostic for macOS/iOS using Apple's Network framework.
// macOS: clang++ -std=c++23 -fobjc-arc tools/ios/lan_path_probe.mm \
//   -framework Foundation -framework Network -o /tmp/nfsmw-lan-path
// Run: /tmp/nfsmw-lan-path <IPv4/hostname> <TCP port>
#import <Foundation/Foundation.h>
#import <Network/Network.h>
#include <cstdio>
#include <memory>
#include <mutex>
#include <string>

int main(int argc, char** argv) {
  @autoreleasepool {
    if (argc != 3) { std::fprintf(stderr, "usage: lan_path_probe host port\n"); return 2; }
    auto endpoint = nw_endpoint_create_host(argv[1], argv[2]);
    auto parameters = nw_parameters_create_secure_tcp(NW_PARAMETERS_DISABLE_PROTOCOL,
                                                       NW_PARAMETERS_DEFAULT_CONFIGURATION);
    nw_connection_t connection = nw_connection_create(endpoint, parameters);
    if (!connection) return 2;
    auto queue = dispatch_queue_create("nfsmw.path.probe", DISPATCH_QUEUE_SERIAL);
    auto done = dispatch_semaphore_create(0);
    struct Result { std::mutex mutex; bool ready = false; int reason = 0; };
    auto result = std::make_shared<Result>();
    // Removed explicitly before returning; no callback holds a dangling stack.
    nw_connection_set_state_changed_handler(connection, ^(nw_connection_state_t state, nw_error_t error) {
      auto path = nw_connection_copy_current_path(connection);
      int reason = path ? nw_path_get_unsatisfied_reason(path) : 0;
      std::printf("state=%d error_domain=%d error=%d path_status=%d unsatisfied_reason=%d wifi=%d\n",
          int(state), error ? int(nw_error_get_error_domain(error)) : 0,
          error ? nw_error_get_error_code(error) : 0,
          path ? int(nw_path_get_status(path)) : 0, reason,
          path ? nw_path_uses_interface_type(path, nw_interface_type_wifi) : false);
      std::fflush(stdout);
      {
        std::lock_guard<std::mutex> guard(result->mutex);
        result->ready = result->ready || state == nw_connection_state_ready;
        if (reason) result->reason = reason;
      }
      if (state == nw_connection_state_ready || state == nw_connection_state_failed ||
          reason == nw_path_unsatisfied_reason_local_network_denied) dispatch_semaphore_signal(done);
    });
    nw_connection_set_queue(connection, queue);
    nw_connection_start(connection);
    bool timeout = dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 5 * NSEC_PER_SEC)) != 0;
    nw_connection_cancel(connection);
    nw_connection_set_state_changed_handler(connection, nullptr);
    dispatch_sync(queue, ^{});
    std::lock_guard<std::mutex> guard(result->mutex);
    std::printf("host=%s port=%s timeout=%d connected=%d local_network_denied=%d\n", argv[1], argv[2], timeout,
                result->ready, result->reason == nw_path_unsatisfied_reason_local_network_denied);
    return result->ready ? 0 : 1;
  }
}
