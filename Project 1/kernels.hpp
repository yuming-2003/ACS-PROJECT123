
#pragma once
#include <cstddef>
#include <cstdint>
#include <cmath>
#include <algorithm>

// Arithmetic intensity (FLOPs per element) helpers per kernel
// SAXPY: y = a*x + y  -> 1 mul + 1 add = 2 FLOPs/element
inline double flops_per_elem_saxpy() { return 2.0; }
// Dot: s += x*y -> 1 mul + 1 add = 2 FLOPs/element
inline double flops_per_elem_dot() { return 2.0; }
// Elemwise multiply: z = x*y -> 1 FLOP
inline double flops_per_elem_mul() { return 1.0; }
// 1D 3-point stencil: y[i]=a*x[i-1]+b*x[i]+c*x[i+1] -> 3 mul + 2 add = 5 FLOPs
inline double flops_per_elem_stencil3() { return 5.0; }

// Kernels: scalar loops. Auto-vectorized build should vectorize these.
// Stride parameter applies to x/y/z where relevant (>=1). Misalignment is controlled by pointer offsets.

template<class T>
inline void kernel_saxpy(std::size_t N, T a, const T* __restrict x, T* __restrict y,
                         std::size_t stride=1)
{
    for (std::size_t i=0; i<N; ++i) {
        const auto xi = x[i*stride];
        y[i*stride] = a*xi + y[i*stride];
    }
}

template<class T>
inline T kernel_dot(std::size_t N, const T* __restrict x, const T* __restrict y,
                    std::size_t stride=1)
{
    T s = T(0);
    for (std::size_t i=0; i<N; ++i) {
        s += x[i*stride] * y[i*stride];
    }
    return s;
}

template<class T>
inline void kernel_mul(std::size_t N, const T* __restrict x, const T* __restrict y,
                       T* __restrict z, std::size_t stride=1)
{
    for (std::size_t i=0; i<N; ++i) {
        z[i*stride] = x[i*stride] * y[i*stride];
    }
}

// Neumann boundary (copy ends). For N>=2.
template<class T>
inline void kernel_stencil3(std::size_t N, T a, T b, T c,
                            const T* __restrict x, T* __restrict y, std::size_t stride=1)
{
    if (N == 0) return;
    if (N == 1) { y[0] = b*x[0]; return; }

    // interior
    for (std::size_t i=1; i<N-1; ++i) {
        const auto xim1 = x[(i-1)*stride];
        const auto xi   = x[i*stride];
        const auto xip1 = x[(i+1)*stride];
        y[i*stride] = a*xim1 + b*xi + c*xip1;
    }
    // boundaries
    y[0]         = b*x[0];
    y[(N-1)*stride] = b*x[(N-1)*stride];
}
