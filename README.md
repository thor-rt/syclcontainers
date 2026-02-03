Docker containers for SYCL implementations.

## AdaptiveCpp Containers

* **adaptivecpp-base**: Base AdaptiveCpp container with CPU backend
* **adaptivecpp-hpc**: AdaptiveCpp with HDF5 and OpenMPI

## Intel SYCL Containers

* **intel-sycl-base**: Base Intel DPC++ container with Intel oneAPI HPC Toolkit
* **intel-sycl-hpc**: Intel DPC++ with HDF5 and Intel MPI

### OpenCL Backend Selection (intel-sycl-base)

The container includes both Intel OpenCL and PoCL backends. Intel OpenCL is used by default and PoCL is hidden from SYCL.

```bash
# Use Intel OpenCL (default)
./my_sycl_app

# Show all available OpenCL platforms (including PoCL)
SYCL_DEVICE_ALLOWLIST='' sycl-ls

# Use PoCL instead of Intel OpenCL
ONEAPI_DEVICE_SELECTOR='opencl:1' ./my_sycl_app

# Or force PoCL only via OpenCL ICD
OCL_ICD_FILENAMES=/opt/pocl/lib/libpocl.so.2 ./my_sycl_app
```

**Note:** The Intel SYCL runtime filters non-Intel OpenCL platforms by default. Use `SYCL_DEVICE_ALLOWLIST=''` to see all platforms, or `ONEAPI_DEVICE_SELECTOR` to select a specific backend.

## Testing

Run the test suite inside a container:

```bash
# Intel containers
docker run --rm -v ./tests:/tests intel-sycl-base bash -c "source /opt/intel/oneapi/setvars.sh && /tests/run_tests.sh"

# AdaptiveCpp containers
docker run --rm -v ./tests:/tests adaptivecpp-base /tests/run_tests.sh
```
