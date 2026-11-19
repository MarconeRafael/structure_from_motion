# Selection Overhead, Profile Coverage, and Fixed-Point Error in a Simulated Structure-from-Motion Kernel

## Abstract

We evaluate a Python manager that selects between NumPy float64 and simulated
VHDL Q15.16 implementations of the essential matrix calculation. On 16 held-out
inputs and four repetitions, the median decision time in the balanced Windows
scenario decreased from 15.68 ms to 1.40 ms after signature caching. Coverage
remained 56/64 for the conservative policy and reached 64/64 with an optional
software attempt validated after execution. Under a 5 ms budget the original,
cached, and cached-with-verification policies delivered 0, 56, and 64 valid results
out of 64, respectively. Fixed software delivered 64 and had the lowest time
in this scenario. The WSL replication also reduced decision time, with the
optimized manager still exceeding 5 ms. Across 108 additional synthetic inputs, RTL matched the
integer model bit for bit. Eight inputs overflowed and 71 of 100 nonoverflowing
outputs crossed a descriptive shape error threshold or had undefined shape.
The results quantify the cost of identity checks, empirical profile coverage,
and the sensitivity of an epipolar kernel to scale and quantization.

## Introduction

The essential matrix of a calibrated two-view problem can be computed as
(E=K^\top F K) when both cameras share intrinsics (K). The calculation is small
enough that the work involved in selecting and invoking a backend can matter
more than the multiplication. This case study asks how much of the measured
selection time can be removed by reusing verified signatures, which cases a
manager then accepts, and how fixed-point error depends on input scale.
The hypotheses are that signature validation dominates the original warm
decision time and that exact agreement with an integer model can coexist
with substantial error relative to the geometric reference.

## Related Work

StarPU uses empirical models to schedule work across heterogeneous processors,
and MAUI uses profiles in a constrained offload decision. These techniques
establish prior art for runtime selection. The present comparison concerns a
local matrix kernel and includes the time to verify software and tool identity.
[Augonnet et al.](https://doi.org/10.1002/cpe.1631) ·
[Cuervo et al.](https://doi.org/10.1145/1814433.1814441).

Python-based RTL verification with cocotb has been applied to detector
electronics. Formal error analysis in Rosa can select a representation that
meets a numerical specification. Our methodology compares a float64 reference,
an integer model, and an independent simulator output for a fixed representation.
The resulting empirical profiles describe the measured workload.
[Rosser](https://doi.org/10.48550/arXiv.1910.06694) ·
[Darulova and Kuncak](https://doi.org/10.1145/3014426).

Hartley demonstrated the value of coordinate normalization in fundamental
matrix estimation. Komorkiewicz et al. implemented a larger SfM pipeline on
an FPGA–ARM SoC and studied resource, frequency, and accuracy trade-offs.
Our controlled experiment isolates the effect of applying fixed-point
arithmetic after obtaining F. The arithmetic and runtime observations
refer to behavioral simulation. [Hartley](https://doi.org/10.1109/34.601246) ·
[Komorkiewicz et al.](https://doi.org/10.1109/DASIP.2015.7367241).

## System Architecture

Python receives F and K and can compute E directly with NumPy. The RTL
adapter encodes 3×3 matrices into signed Q15.16 values, writes an input file,
and launches GHDL. The testbench applies synchronous reset and samples
valid binary outputs on the prescribed clock edge. TextIO exports the nine
signed values. An independent integer model uses signed-64 accumulation and
the signed-32 slice for both multiplications. Quantization, truncation and
wrap follow the verified arithmetic contract. The adapter rejects undefined
signals and checks each output against the integer model. Numerical overflow
invalidates the result even when all nine integers match.

## Constraint-Based Selection

The conservative manager identifies compatible profiles by backend signature,
input class and component-wise envelope. It filters candidates with observed
failures and uses the maximum observed error and runtime for the remaining
candidates. It ranks eligible candidates by time or prioritizes simulated RTL
when requested. A selection is validated after execution, including elapsed
decision and recovery time when a time budget applies.

The cache stores verified signatures per instance. It resolves the executable
and checks source and executable metadata plus configuration on each lookup.
On a change, it recomputes the signature, including an executable digest for
RTL. The optional software attempt runs when no candidate is selected and
software lacks a compatible profile. It records the absence of a prior
prediction and returns a result only after numerical and time validation.

## Experimental Methodology

The original study used 33 characterization, 10 development and 16 final
inputs. It included numerical stress cases, calibrated synthetic poses and
one image pair. The paired experiment reuses the held-out inputs and
predeclared scenarios. On each platform both managers use identical new
characterization observations and their respective implementation signatures.
We execute the archived manager, the cached manager, the cached manager
with optional software verification, and fixed software and RTL baselines
four times per final case and scenario. Seeded ordering interleaves variants.
The first cache fill is measured on a development input. Paired overhead
subtracts the total time of the corresponding fixed-software request.

Additional geometric data use independent seeds for characterization,
development and evaluation. The final set crosses three focal lengths,
three translation magnitudes, three noise levels and four scales of F.
Each scene has known intrinsics and pose, and positive depth in both views.
For noisy correspondences we estimate F in OpenCV. The known pose supplies
a theoretical E for every case. A normalized Frobenius distance minimizes
over both signs. We report the distance of RTL from float64 and the distance
of both from the theoretical E. We flag a descriptive threshold of 0.1 or
undefined shape due to a zero output in the nonoverflowing group.

## Results

The archived study recorded 32/32 bit-exact outputs, six invalid observations
with overflow and a median paired software latency of 38.75 µs versus
87.84 ms for simulated RTL. Its recorded balanced overhead of 15.21 ms
belongs to that run. The new paired Windows run measured 15.67 ms for the
original and 1.38 ms for the optimized manager, subtracting the matched fixed
software request. Median signature checking fell from 15.38 ms to 1.16 ms.
The first cached decision took 60.97 ms. The balanced p95 decision times
were 17.93 ms and 2.02 ms, respectively. [Historical data](RESULTS.md) ·
[Paired data and plots](STAGE4.md).

Without a time budget the optimized and original conservative variants made
the same choices. The balanced variant missed eight feasible requests because
two final inputs fell outside the successful profiles. The software verification
option recovered these eight requests and recorded each as an execution without
prior coverage. With a 5 ms bound the original manager exceeded the decision
budget. The cached manager completed all 56 requests covered by compatible
profiles and the verification option completed all 64. Every variant declined
or failed the zero-time scenario under its own execution rules.

On WSL with GHDL 1.0.0 and the repository mounted from Windows, balanced
median decision time decreased from 151.91 ms to 30.72 ms. The balanced
coverage counts matched Windows. Under the 5 ms budget all three managed
variants returned zero valid results and fixed software delivered 64/64.
The two platform runs produced the same 108 integer matrices on the
additional synthetic inputs. [WSL data](../experiments/stage4_results/20261119T175314057268Z/summary.json).

All 108 new final synthetic outputs were bit-exact. With F scaled by 0.01,
11 outputs had undefined shape because they were zero, and the other 16
exceeded the 0.1 threshold. At scale 1, 26/27 exceeded the threshold. At
scale 100, 18/27 exceeded it. At scale 100,000, eight overflowed and the
remaining 19 had a median shape error of 0.000794 against float64. At scale
1, median float64 shape distance from the known pose was approximately
zero, 0.302 and 0.568 at the three noise levels. This separates the error
already present upstream in F from the difference due to RTL arithmetic.

## Discussion

Signature verification was responsible for most of the original selection
time. Reuse reduced steady-state cost enough to change decisions under a 5 ms
budget. The same mechanism preserves the profile boundary in the balanced
scenario. Coverage recovered only when the policy explicitly permitted a
software attempt with post-execution validation. Fixed software remained
faster and was viable whenever the optimized policy delivered a valid
balanced result. These outcomes support a descriptive case study of
validation overhead and profile coverage.

Increasing the magnitude of F changes which values survive quantization,
even though the ideal epipolar relation is equivalent up to scale. The
largest tested factor produced low shape error among surviving results
alongside eight overflows. Selecting a scale based on that result would
require a new predeclared method and separate evaluation.

## Threats to Validity

Times depend on process startup, filesystem and toolchain. The simulator
timeout and measured request budgets provide no real-time guarantee. The
same 16 final cases are repeated and a preprocessing step shares the only
real image pair. Synthetic geometries provide known poses but cover a limited
set of camera configurations. The shape threshold does not have an established
correspondence to errors in pose, triangulation or 3D reconstruction. The
four scales share each scene, while scenes are resampled between noise levels.
Noise-level comparisons are descriptive. The
fixed software baseline defines the absolute numerical reference for policy
evaluation. The separately computed theoretical E provides the independent
synthetic comparison. The study measures only software and RTL simulation.

## Conclusion

Caching implementation signatures substantially reduced warm selection time
and opened a previously unattainable budget for covered requests. A
post-validated software attempt addressed profile coverage gaps at a
separate and measured cost. The expanded geometry experiment demonstrated
both quantization-induced shape distortion and overflow despite exact RTL
agreement with its integer reference.

Before submission, replicate the performance comparison on independent
hosts, broaden the real calibrated scenes, relate shape error to pose or
reconstruction metrics, and situate the contribution in a wider literature
review. The evidence currently supports the stated case study.
[Reproduction and evidence](STAGE4.md) · [Related-work notes](RELATED_WORK.md).
