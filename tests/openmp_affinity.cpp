// Exercise host OpenMP initialization before a real SYCL CPU kernel. [AI-Codex]
#include <link.h>
#include <omp.h>
#include <sched.h>
#include <sycl/sycl.hpp>
#include <sys/syscall.h>
#include <unistd.h>

#include <cstdint>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <thread>

struct Sample {
    int cpu;
    long tid;
    std::uint32_t value;
};

std::set<std::string> openmpLibraries() {
    std::set<std::string> libraries;
    dl_iterate_phdr(
        [](dl_phdr_info *info, std::size_t, void *data) {
            std::string path = info->dlpi_name;
            const auto name = path.substr(path.find_last_of('/') + 1);
            if (name.find("libomp.so") == 0 || name.find("libgomp.so") == 0 ||
                name.find("libiomp5.so") == 0) {
                static_cast<std::set<std::string> *>(data)->insert(path);
            }
            return 0;
        },
        &libraries);
    return libraries;
}

bool runKernel(const std::set<int> &allocation, int threads) {
    sycl::queue queue{sycl::cpu_selector_v};
    constexpr int size = 65536;
    auto *samples = sycl::malloc_shared<Sample>(size, queue);
    if (!samples)
        throw std::bad_alloc{};
    for (int i = 0; i < size; ++i)
        samples[i] = {-1, -1, 0};
    // This test selects only the Linux CPU backend. Record placement inside
    // the kernel, so a successful vector addition on one CPU cannot pass.
    queue
        .parallel_for(sycl::range<1>{size},
                      [=](sycl::id<1> i) {
                          samples[i].cpu = sched_getcpu();
                          samples[i].tid = syscall(SYS_gettid);
                          samples[i].value =
                              static_cast<std::uint32_t>(i[0]) * 1664525u + 1013904223u;
                      })
        .wait_and_throw();
    std::set<int> used_cpus;
    std::set<long> used_threads;
    bool correct = true;
    for (int i = 0; i < size; ++i) {
        used_cpus.insert(samples[i].cpu);
        used_threads.insert(samples[i].tid);
        correct = correct && samples[i].tid > 0 &&
                  samples[i].value == static_cast<std::uint32_t>(i) * 1664525u + 1013904223u;
    }
    sycl::free(samples, queue);
    std::cout << "requested=" << threads << " kernel_threads=" << used_threads.size()
              << " kernel_cpus=" << used_cpus.size() << '\n';
    for (int cpu : used_cpus)
        std::cout << "cpu=" << cpu << ' ';
    std::cout << '\n';
    const auto libraries = openmpLibraries();
    for (const auto &path : libraries)
        std::cout << "OpenMP runtime: " << path << '\n';
    const bool one_llvm_runtime =
        libraries.size() == 1 && libraries.begin()->find("/libomp.so") != std::string::npos;
    if (!one_llvm_runtime)
        std::cerr << "FAIL: expected only LLVM libomp in the running process\n";
    if (used_cpus != allocation)
        std::cerr << "FAIL: kernel did not use exactly its assigned CPUs\n";
    return correct && one_llvm_runtime && used_cpus == allocation &&
           used_threads.size() == static_cast<unsigned>(threads);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "Usage: openmp_affinity <comma-separated assigned CPUs>\n";
        return 1;
    }
    try {
        std::set<int> allocation;
        std::istringstream input(argv[1]);
        std::string cpu;
        while (std::getline(input, cpu, ','))
            allocation.insert(std::stoi(cpu));
        // Initialize host OpenMP before creating SYCL queues.
        const int threads = omp_get_max_threads();
        if (threads < 2 || allocation.size() != static_cast<unsigned>(threads)) {
            std::cerr << "FAIL: test requires at least two CPUs and one thread per assigned CPU\n";
            return 1;
        }
        bool passed = false;
        std::exception_ptr error;
        // The submitting thread inherits the initial OpenMP thread's binding.
        std::thread submitter([&] {
            try {
                passed = runKernel(allocation, threads);
            } catch (...) {
                error = std::current_exception();
            }
        });
        submitter.join();
        if (error)
            std::rethrow_exception(error);
        std::cout << (passed ? "PASS" : "FAIL") << '\n';
        return passed ? 0 : 1;
    } catch (const std::exception &error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
}
