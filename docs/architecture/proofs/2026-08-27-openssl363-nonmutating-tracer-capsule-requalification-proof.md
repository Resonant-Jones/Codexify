# Requalification of the non-mutating tracer capsule with a validated child-map control

**Date:** 2026-08-27
**Execution lane:** Architecture-Impact
**Task kind:** proof
**Requested evidence posture:** live-runtime proven
**Achieved evidence posture:** live runtime observed for the bounded instrumentation controls
**Result:** PASS
**Primary classification:** OPENSSL_SOURCE_READ_TRACER_CAPSULE_QUALIFIED
**Confidence:** High for this exact disposable builder/verifier run, the two bounded controls, verifier preservation, retained-artifact integrity, and cleanup. This does not establish an OpenSSL cause or release readiness.

## Decision

One Linux/arm64 strace runtime capsule was built in one disposable builder from the
exact qualified immutable backend image. It was mounted read-only into one fresh
verifier that had the accepted OpenSSL build-dependency posture but no strace
package. The verifier had CAP_SYS_PTRACE and Docker default seccomp only.

Before the one traced runtime-isolation control, a temporary Perl child-map program
was syntax checked and then run exactly once directly through the verifier's base
Perl. It proved that the same child derived and read /proc/<actual-pid>/maps and
emitted loader and libc evidence. The one subsequent traced run of that same file
again emitted coherent child PID/map evidence and showed only verifier/base-runtime
loader and libc mappings. The one synthetic File::Copy trace then showed source and
destination descriptors, destination creation with truncation, a nonzero read/write
transfer, returned byte counts, and closes. The frozen verifier package/runtime
identity was unchanged afterward.

The capsule was retained only after all those gates passed. No OpenSSL, Node, Pi,
OAuth, OpenAI, provider, credential, Compose, or application path was invoked.

## Authority, lineage, and release boundary

| Field | Value |
| --- | --- |
| Proof branch | proof/openssl363-nonmutating-tracer-capsule-requalification |
| Task base HEAD | 3c56cba985e97fc52f017fe680b86bdb63096015 |
| Observed origin/main | 3c56cba985e97fc52f017fe680b86bdb63096015 |
| Fetch | git fetch origin main attempted once; passed |
| Immediate predecessor | 73b3fe08b7a93060ad22032d09afe6cca7bd43d4 |
| Source-read blocked predecessor | 54e9c89b7da4212b9c43adc8726755fabd358bda |
| Operation-trace predecessor | 927eed965f7655e8564ec4bf4052d380e8abb3c7 |
| Additional inspected predecessors | 9a319684b52444d87cb7c9b1e0fda31dd6e5ae29; 96c59ab8411eb5cd8538ec0625d4824cc47d04bb |
| Governing material | 00-current-state, ADR index, Architecture KB, Config and Ops, Agent Protocol Operations, Pi Invocation Boundary, Agent Tool Loop |
| Relevant ADRs resolved | ADR-020, ADR-066, ADR-068 |
| ADR impact | No ADR impact |

This is an Internal proof-only instrumentation qualification. It changes no Guardian
authority, runtime contract, persistence, queue/worker behavior, provider routing,
supported profile, Docker topology, current-state document, or release claim.
00-current-state remains release truth.

## Qualified substrate and Docker authority

| Field | Result |
| --- | --- |
| Qualified immutable image | sha256:2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf |
| Image inspection | linux arm64; PASS |
| Retained backend archive | /Volumes/Dev_SSD/codexify-proof-images/backend-openssl-substrate-2508fe43e87e883caea01fe36b5ab5eff3a1d9616d395d7e7903b03204a584cf.tar |
| Backend archive initial/final SHA-256 | 689a3cb56fc688cca5ecd55ba946aa63bbdbea3dee2d42139606269c27a7df1c; PASS |
| Backend archive load count | 0 |
| Docker context | desktop-linux |
| Docker client/server | 29.7.2 / 29.7.2 |
| Docker server platform | linux/arm64 |
| Scratch root | /Volumes/Dev_SSD/codexify-strace-requal.Pw9zVR; removed |

No mutable tag, image pull, image build, image commit, image prune, Docker context
change, daemon restart, or Docker Desktop restart occurred.

## One disposable builder and capsule closure

| Field | Result |
| --- | --- |
| Builder container ID / count | a89dce6b03480abfc5c008325abb441c05eb55710dd4046fa58fff0867bac844 / 1 |
| Builder entrypoint | explicit inert /bin/sh loop |
| Builder OpenSSL executions | 0 |
| Builder package transaction | apt-get update; DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends strace binutils |
| Package origin | Debian trixie arm64 |
| strace version / architecture | 6.13+ds-1 / arm64 |
| strace SHA-256 | e4f0c42a07574df2fc6b353f5bc24423099d8c896cee72c605671d878fedeb5a |
| ELF class / machine | ELF64 / AArch64 |
| ELF interpreter | /lib/ld-linux-aarch64.so.1 |
| Runtime closure | /usr/bin/strace; /lib/ld-linux-aarch64.so.1; /lib/aarch64-linux-gnu/libc.so.6 |
| Capsule manifest SHA-256 | 1088d7817a6d8b1d1e8b2f1f091c1343fd1516cd585769060a1e51c1c8e47910 |
| Capsule pre-retention SHA-256 | 1509165cf1ee3213598d17ff2eaba804199644ded601fe11c3c8d951b9255c33 |

The copied loader successfully invoked the copied tracer with its copied libc
closure. The bounded manifest contained:

~~~text
e4f0c42a07574df2fc6b353f5bc24423099d8c896cee72c605671d878fedeb5a  usr/bin/strace
b205e699bb1eba36c7472c19637a01fe79be25e7d16f0ed205b66b5ffed586f2  lib/ld-linux-aarch64.so.1
206168570f3c8f63f04ebb47ce27c7fc494aba6fc7696592c79c04b7fe2ba390  lib/aarch64-linux-gnu/libc.so.6
~~~

## One fresh verifier and frozen identity

| Field | Result |
| --- | --- |
| Verifier container ID / count | 6c31380de46b39c594cd5b92c809ea7b032e39dadc75f061ea4c24dd482ea489 / 1 |
| Entrypoint | explicit inert /bin/sh loop |
| Capability/security posture | CAP_SYS_PTRACE; default seccomp; SecurityOpt=null |
| Writable mount | task-owned /work |
| Capsule mount | /opt/codexify-tracer, read-only |
| Global loader variables | LD_LIBRARY_PATH and LD_PRELOAD absent/unset |
| Verifier strace before/after controls | absent |
| Dependency request | perl, perl-modules-5.40, build-essential, binutils, ca-certificates, ninja-build, python3 |
| File::Spec::Functions before trace | FILE_SPEC_FUNCTIONS_OK; PASS |

The exact accepted dependency sequence was:

~~~text
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends perl perl-modules-5.40 build-essential binutils ca-certificates ninja-build python3
~~~

No tracer or diagnostic package was added to the verifier.

| Frozen component | Resolved path | SHA-256 |
| --- | --- | --- |
| Package manifest | deterministic dpkg-query sort | 2b668f8804e85f3c6100d8ee3f9910a7f8929b97f09fc0057459405210153ee5 |
| Perl | /usr/bin/perl | 470d3a7bbd741953e05de861c3d06067118bd6c0991c4a7c60f008448fdf5afa |
| libc | /usr/lib/aarch64-linux-gnu/libc.so.6 | 9a325944115b36e74077786b29531963d96cd55cd6c82f11750a352cdb58fab0 |
| make | /usr/bin/make | 442d0d9908e6e1968a2e1f9a82aad5231ff6b02deb3071ce38750e2e2f7a2a45 |
| Compiler driver | /usr/bin/aarch64-linux-gnu-gcc-14 | fb051a6c58961fb6aec758acf50d7d0375eecff740d0706388092829e3fb7a41 |
| Linker | /usr/bin/aarch64-linux-gnu-ld.bfd | 5a284e435cdf41bc05d93f0683da12b8a42608b93c79e187e7d03fab6a22ddf4 |

## Corrected child-map control and direct preflight

The temporary file /work/child-map-control.pl was the only child-map control and
was not added to the repository:

~~~perl
use strict;
use warnings;

my $pid = $$;
my $maps_path = "/proc/$pid/maps";

open my $fh, "<", $maps_path
    or die "cannot open $maps_path: $!";

my @lines = <$fh>;
close $fh;

my @loader = grep {
    /ld-linux|ld-[^\/\s]*\.so/
} @lines;

my @libc = grep {
    /\/libc\.so/
} @lines;

print "SELF_PID=$pid\n";
print "MAPS_PATH=$maps_path\n";

die "no loader mapping found\n" unless @loader;
die "no libc mapping found\n" unless @libc;

print "LOADER_MAP=$loader[0]";
print "LIBC_MAP=$libc[0]";
~~~

The literal /proc/$$/maps was absent. A first host-shell materialization attempt
was rejected by shell parsing before execution; it created no verifier program and
consumed no syntax, preflight, or traced control. The control above was then
materialized directly in task scratch.

| Gate | Result |
| --- | --- |
| Child-map syntax checks | 1; syntax OK |
| Direct non-traced preflights | 1 |
| Direct child PID | 792 |
| Direct maps path | /proc/792/maps |
| Direct loader mapping | /usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 |
| Direct libc mapping | /usr/lib/aarch64-linux-gnu/libc.so.6 |
| PID decimal / map path matches PID | PASS / PASS |
| Loader / libc evidence | PASS / PASS |
| Literal-path rejection | PASS |

~~~text
SELF_PID=792
MAPS_PATH=/proc/792/maps
LOADER_MAP=ffffaf208000-ffffaf230000 r-xp 00000000 00:2d7 1388491                   /usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1
LIBC_MAP=ffffaefa0000-ffffaf13c000 r-xp 00000000 00:2d7 1388497                   /usr/lib/aarch64-linux-gnu/libc.so.6
~~~

## Sole traced runtime-isolation control

After preflight passed, the same child-map file ran exactly once through the
capsule loader/runtime, with child stdout separate from the syscall trace:

~~~text
unset LD_LIBRARY_PATH LD_PRELOAD
/opt/codexify-tracer/lib/ld-linux-aarch64.so.1 \
  --library-path /opt/codexify-tracer/lib/aarch64-linux-gnu \
  /opt/codexify-tracer/usr/bin/strace \
  -f -qq -e trace=execve -o /work/runtime-isolation.strace -- \
  /usr/bin/perl /work/child-map-control.pl
~~~

| Gate | Result |
| --- | --- |
| Traced runtime-isolation controls / retries | 1 / 0 |
| Traced child PID / maps path | 822 / /proc/822/maps |
| Traced loader path | /usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1 |
| Traced libc path | /usr/lib/aarch64-linux-gnu/libc.so.6 |
| Capsule-library mappings in traced child | 0 |
| Traced child uses base runtime | PASS |

~~~text
SELF_PID=822
MAPS_PATH=/proc/822/maps
LOADER_MAP=ffffb4260000-ffffb4288000 r-xp 00000000 00:2d7 1388491                   /usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1
LIBC_MAP=ffffb3ff0000-ffffb418c000 r-xp 00000000 00:2d7 1388497                   /usr/lib/aarch64-linux-gnu/libc.so.6
execve("/usr/bin/perl", ["/usr/bin/perl", "/work/child-map-control.pl"], ...) = 0
~~~

The child loader and libc maps belong to the verifier/base runtime and do not
resolve beneath /opt/codexify-tracer.

## Transfer control and sole synthetic transfer trace

The separate temporary /work/transfer-control.pl was syntax checked once before
its one live execution. It accepted explicit arguments and used File::Copy:

~~~perl
use strict;
use warnings;
use File::Copy qw(copy);

my ($source, $destination) = @ARGV;
die "usage: $0 <source> <destination>\n"
    unless defined $source && defined $destination && @ARGV == 2;

copy($source, $destination)
    or die "copy $source -> $destination failed: $!\n";
~~~

The syntax check passed and performed no copy. After runtime isolation passed, the
one 118-byte sentinel source ran through the capsule tracer with -yy and exactly
this operation filter:

~~~text
openat,newfstatat,fstat,statx,read,pread64,readv,lseek,copy_file_range,sendfile,splice,write,pwrite64,writev,ftruncate,truncate,rename,renameat,renameat2,close,fsync,fdatasync
~~~

No payload-dump option was enabled: -x, -xx, -s, and explicit read/write dump
options were omitted. The receipt intentionally records normalized observations
rather than buffer content:

~~~text
openat(..., "/work/synthetic-source.bin", O_RDONLY|O_CLOEXEC) = 3</work/synthetic-source.bin>
openat(..., "/work/synthetic-destination.bin", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666) = 4</work/synthetic-destination.bin>
read(3</work/synthetic-source.bin>, <buffer omitted>, 1024) = 118
write(4</work/synthetic-destination.bin>, <buffer omitted>, 118) = 118
close(4</work/synthetic-destination.bin>) = 0
close(3</work/synthetic-source.bin>) = 0
~~~

| Gate | Result |
| --- | --- |
| Transfer-control syntax checks | 1; PASS |
| Traced transfer controls / retries | 1 / 0 |
| Source open / destination open / truncation | PASS / PASS / PASS |
| Effective primitive | read/write |
| Read requested / returned bytes | 1024 / 118 |
| Write requested / returned bytes | 118 / 118 |
| Close observation | PASS |
| Synthetic source size / SHA-256 | 118 / 14922b66d1bfb98311c00504a323ce3e0091b83276245cacfd18ecd32dfb03b0 |
| Synthetic destination size / SHA-256 | 118 / 14922b66d1bfb98311c00504a323ce3e0091b83276245cacfd18ecd32dfb03b0 |
| Source/destination equality | PASS |
| Payload-dump status | no payload-dump option enabled |

## Post-trace verifier preservation

The package manifest recomputed after both controls exactly matched its pre-trace
value. All five critical runtime paths and hashes also matched the frozen values.

~~~text
VERIFIER_PACKAGE_MANIFEST_PRE_SHA256:  2b668f8804e85f3c6100d8ee3f9910a7f8929b97f09fc0057459405210153ee5
VERIFIER_PACKAGE_MANIFEST_POST_SHA256: 2b668f8804e85f3c6100d8ee3f9910a7f8929b97f09fc0057459405210153ee5
VERIFIER_PACKAGE_MANIFEST_EQUAL: PASS
VERIFIER_CRITICAL_RUNTIME_HASHES_EQUAL: PASS
TRACER_PACKAGE_INSTALLS_IN_VERIFIER: 0
TRACER_PACKAGE_UPGRADES_IN_VERIFIER: 0
VERIFIER_RUNTIME_IDENTITY_PRESERVED: PASS
FILE_SPEC_FUNCTIONS_OK
~~~

No tracer-caused package change, direct ldconfig invocation, or system-library
write occurred after identity freeze.

## Retention and cleanup

| Field | Result |
| --- | --- |
| Retained capsule | /Volumes/Dev_SSD/codexify-proof-tools/strace-capsule-linux-arm64-1509165cf1ee3213598d17ff2eaba804199644ded601fe11c3c8d951b9255c33.tar |
| Retained checksum | /Volumes/Dev_SSD/codexify-proof-tools/strace-capsule-linux-arm64-1509165cf1ee3213598d17ff2eaba804199644ded601fe11c3c8d951b9255c33.tar.sha256 |
| Pre-retention/final SHA-256 | 1509165cf1ee3213598d17ff2eaba804199644ded601fe11c3c8d951b9255c33; exact match |
| Receipt readback | PASS |
| Existing-digest reuse | no existing matching artifact found |
| Permissions | archive and receipt set read-only, 0444 |
| Builder/verifier/scratch remaining | 0 / 0 / 0 |

The builder, verifier, capsule staging tree, control programs, sentinel files,
traces, manifests, and task scratch root were removed. The qualified backend
image, backend archive, backend receipt, and retained tracer archive/receipt were
preserved. The backend archive was rehashed after cleanup and remained
689a3cb56fc688cca5ecd55ba946aa63bbdbea3dee2d42139606269c27a7df1c.

## Invariants

~~~text
QUALIFIED_IMAGE_IDS_USED: 1
QUALIFIED_ARCHIVE_LOADS: 0
TRACER_BUILDER_COUNT: 1
VERIFIER_COUNT: 1
CONTROL_PROGRAM_SYNTAX_CHECKS: 1
CONTROL_PROGRAM_PREFLIGHTS: 1
TRACED_RUNTIME_ISOLATION_CONTROLS: 1
TRACED_FILE_TRANSFER_CONTROLS: 1
RUNTIME_ISOLATION_CONTROL_RETRIES: 0
FILE_TRANSFER_CONTROL_RETRIES: 0
TRACER_PACKAGE_INSTALLS_IN_VERIFIER: 0
TRACER_PACKAGE_UPGRADES_IN_VERIFIER: 0
VERIFIER_LDCONFIG_RUNS: 0
VERIFIER_SYSTEM_LIBRARY_WRITES: 0
OPENSSL_SOURCE_ACQUISITIONS: 0
OPENSSL_CONFIGURES: 0
OPENSSL_BUILDS: 0
OPENSSL_INSTALL_SW_ATTEMPTS: 0
NODE_SOURCE_ACQUISITIONS: 0
NODE_BUILDS: 0
NODE_EXECUTIONS: 0
PI_EXECUTION_ATTEMPTS: 0
OAUTH_LOGIN_ATTEMPTS: 0
OPENAI_HTTP_REQUESTS: 0
PROVIDER_INFERENCE_REQUESTS: 0
MODEL_PROMPTS: 0
CREDENTIAL_ACCESSES: 0
DOCKER_COMMITS: 0
DOCKER_IMAGE_BUILDS: 0
DOCKER_PRUNE_OPERATIONS: 0
DOCKER_CONTEXT_CHANGES: 0
DOCKER_DAEMON_RESTARTS: 0
DOCKER_DESKTOP_RESTARTS: 0
CANONICAL_NETWORK_MUTATIONS: 0
CANONICAL_VOLUME_MUTATIONS: 0
HOST_PACKAGE_INSTALLATIONS: 0
APPLICATION_SOURCE_EDITS: 0
RELEASE_CLAIM_CHANGES: 0
TASK_OWNED_CONTAINERS_REMAINING: 0
TASK_OWNED_TEMPORARY_IMAGES_REMAINING: 0
TASK_OWNED_TEMPORARY_NETWORKS_REMAINING: 0
TASK_OWNED_TEMPORARY_VOLUMES_REMAINING: 0
TASK_OWNED_SCRATCH_REMAINING: 0
~~~

## Supported statement and next prerequisite

Supported statement:

~~~text
A read-only external strace runtime capsule can observe the required
file-operation boundary without installing tracer packages into the qualified
writer, changing the writer's package/runtime identity, or causing the traced
child to load tracer-capsule runtime libraries. The corrected child-map
control proved its own PID/path semantics before the sole traced runtime
isolation control was consumed.
~~~

This qualifies instrumentation only; it makes no OpenSSL root-cause statement.

Exact next prerequisite:

~~~text
Resume the OpenSSL install-helper source-read-boundary proof using the exact
qualified immutable backend substrate and the retained checksum-verified
tracer capsule. Install no tracer package in the writer. Reuse the qualified
explicit-loader and tracing posture. Execute exactly one OpenSSL configure,
one build, and one traced container-local make install_sw, and stop at the
first source-argument, source-read, transfer, destination-write, or
post-write-replacement divergence.
~~~

Do not perform that OpenSSL run in this task.
