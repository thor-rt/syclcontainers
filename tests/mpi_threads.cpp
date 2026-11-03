// MPI smoke test for the AdaptiveCpp images: two threads per rank, each on its own
// communicator, exchange data concurrently under MPI_THREAD_MULTIPLE. Each send
// and receive uses a contiguous datatype that is freed while the request is
// pending, as MPL does. Prints PASS when every received value is correct. [AI-Claude]
#include <mpi.h>

#include <cstdio>
#include <thread>
#include <vector>

namespace {
constexpr int ROUNDS = 200;
constexpr int COUNT = 4096;

long exchange(MPI_Comm comm, int thread) {
    int rank = 0, size = 0;
    MPI_Comm_rank(comm, &rank);
    MPI_Comm_size(comm, &size);
    const int next = (rank + 1) % size, prev = (rank + size - 1) % size;
    long errors = 0;
    std::vector<double> send(COUNT), recv(COUNT);
    for (int round = 0; round < ROUNDS; ++round) {
        for (int i = 0; i < COUNT; ++i) send[i] = rank * 1e6 + thread * 1e5 + round * 10.0 + i;
        MPI_Datatype type;
        MPI_Type_contiguous(COUNT, MPI_DOUBLE, &type);
        MPI_Type_commit(&type);
        MPI_Request requests[2];
        MPI_Irecv(recv.data(), 1, type, prev, round, comm, &requests[0]);
        MPI_Isend(send.data(), 1, type, next, round, comm, &requests[1]);
        MPI_Type_free(&type);
        MPI_Waitall(2, requests, MPI_STATUSES_IGNORE);
        for (int i = 0; i < COUNT; ++i)
            if (recv[i] != prev * 1e6 + thread * 1e5 + round * 10.0 + i) ++errors;
        long total = 0;
        MPI_Allreduce(&errors, &total, 1, MPI_LONG, MPI_SUM, comm);
    }
    return errors;
}
}  // namespace

int main(int argc, char** argv) {
    int provided = 0;
    MPI_Init_thread(&argc, &argv, MPI_THREAD_MULTIPLE, &provided);
    int rank = 0, size = 0;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (provided != MPI_THREAD_MULTIPLE) {
        if (rank == 0) std::printf("FAIL: MPI_THREAD_MULTIPLE not provided (%d)\n", provided);
        MPI_Finalize();
        return 1;
    }
    MPI_Comm comms[2];
    for (auto& comm : comms) MPI_Comm_split(MPI_COMM_WORLD, 0, rank, &comm);
    long errors[2] = {0, 0};
    std::thread a([&] { errors[0] = exchange(comms[0], 0); });
    std::thread b([&] { errors[1] = exchange(comms[1], 1); });
    a.join();
    b.join();
    long local = errors[0] + errors[1], total = 0;
    MPI_Reduce(&local, &total, 1, MPI_LONG, MPI_SUM, 0, MPI_COMM_WORLD);
    if (rank == 0) std::printf("%s: %d ranks, %ld wrong values\n", total == 0 ? "PASS" : "FAIL", size, total);
    for (auto& comm : comms) MPI_Comm_free(&comm);
    MPI_Finalize();
    return total == 0 ? 0 : 1;
}
