# ES-08 — Operations, Security and Deployment

> **项目**：myknowledgebase（MKB）
>
> **文件 ID**：ES-08
>
> **文档性质**：execution-spec / implementation authority
>
> **版本 / 日期**：ES-08-v1.0 / 2026-08-10
>
> **文档状态**：ready
>
> **Truth 输入**：OT-01-v1.0、OT-02-v1.0、OT-03-v1.0、OT-04-v1.0
>
> **Baseline 输入**：D01-v1.4、D02-v1.0、S01-v1.5、S02-v1.3、S03-v1.3、S04-v1.2、S05-v1.1；S15/S16 没有 frozen 文件
>
> **上游 Execution Spec**：ES-01-v1.0、ES-02-v1.0、ES-03-v1.0、ES-04-v1.0、ES-05-v1.0、ES-06-v1.0、ES-07-v1.0
>
> **上游索引**：docs/specs/index.md

本文件是 MKB v1 单体部署、配置、secret、网络边界、安全、observability、readiness、recovery operation、retention、安全运行包络与总体验收的唯一 Execution Spec。它把 ES-01..07 已冻结的业务合同放进一个可启动、可停止、可备份、可恢复、可审计且 fail-closed 的发布单元中；不重新解释任何 Task、Execution、Process、Intake、Gate、derived asset、vector 或 retrieval Truth。

ES-08 不建设运维平台。V1 只有一个长期运行的 MKB Python 应用、一个 OCI 发布物、一个 embedded Turso 数据库、一个本地 CAS object root，以及同一发布物中的有限 CLI。`/livez`、`/readyz` 与 authenticated metrics 是部署探针，不是产品能力；operator 不能通过 HTTP 改状态、执行 SQL、浏览对象、读取 raw vector 或调用通用 repair。

---

## 1. Inherited Truth

### 1.1 权威输入

| 来源 | 本文件直接继承 | 本文件不得改变 |
|---|---|---|
| OT-01-v1.0 | MKB 是单应用、单发布、standalone knowledge 工具；内部状态与生命周期由 MKB 自持 | 不拆服务，不引入 UI、平台、agent、answer generation、legacy runtime 或上游业务 |
| OT-02-v1.0 | 六个且仅六个 StateFamily；state、fact、proof、pointer、readiness 分账；唯一 owner | 不以 health、incident、operation、backup、secret rotation 或 deployment phase 创建第七 StateFamily |
| OT-03-v1.0 | 简单 internal token；Team 只做隔离/审计而非授权；有限 Task/poll/retrieval Contract；raw vector OOS | 不建设 RBAC、session、callback、operator product API、raw storage/vector API |
| OT-04-v1.0 | 全链成功、失败可解释、crash/replay 收敛、零 legacy 依赖、有限 semantic usefulness release gate | 不把 log、metric、HTTP 200、backup file 或 benchmark 数字冒充业务成功或 Owner SLA |
| D01/D02 | control 向下、typed outcome/proof 向上；owner guard 与非法边 fail-closed | recovery 不得直改别域 status、猜 proof 或跨 owner 补 truth |
| S01/S02 | token validity、Team gate、Task contract、polling、idempotency、structured errors | token 不得隐式 team-scoped；运维面不得泄漏资源存在性 |
| S03 | lease/fence/retry/recovery、semantic scanner、summary-before-cleanup | scheduler/health/queue/log 不成为 runtime truth |
| S04/S05 | canonical Intake、artifact/proof、logical-first lifecycle、greenfield bootstrap、drift拒绝 readiness | 不从 physical residue、mtime、provider response或文件重建 Snapshot/Revision |
| ES-01..07 | exact API、Workflow、Process、schema、provider、LS-RAG、vector/retrieval、事务与对象协议 | 只落成 runtime guard、配置、资源、监控、runbook 与总验收；不增加 intent/source/Workflow/Process capability |

Baseline 中 S15/S16 只有待建范围，没有 frozen truth 文件。本文件继承其已经由 S01..05 明确移交的义务：trace 必须贯穿、失败不能只存在日志字符串、简单认证仍有安全边界、URL fetch 必须防 SSRF、secret 不可落库/入日志、readiness 必须拒绝 drift。旧 S15/S16 的 `operator API` 候选不具有 truth 权；V1 选择 local finite CLI，而不是网络控制面。

### 1.2 Truth 到交付物映射

| Truth cluster | 本文件落点 |
|---|---|
| 单应用/单发布/零 legacy | §4.1、§4.10、§7、§8.1/8.10 |
| simple token + Team 隔离 | §4.3/4.4、§5.3/5.8、§8.2/8.3 |
| strict ingress、bounded request、safe error | §4.4/4.6、§5.8、§6.4、§8.3 |
| source/provider egress 与 SSRF | §4.5、§5.6、§6.5、§8.4 |
| startup/schema/registry/workflow drift | §4.7、§6.3、§8.5/8.8 |
| observability 不是 Truth | §4.9、§5.9、§6.1/6.2、§8.6 |
| crash、shutdown、recovery、backup | §4.8/4.11、§6.6..6.9、§8.5/8.7 |
| cleanup/retention | §4.12、§6.7/6.10、§8.7 |
| semantic usefulness 与总体验收 | §4.10、§8.9/8.10、§9.2/9.3 |
| measured safe envelope，不是 SLA | §4.6、§8.9、§9.1/9.2 |

### 1.3 唯一 ownership

| Concern | 唯一 owner | ES-08 权限 |
|---|---|---|
| Team/Task/API/error | ES-01 | 实现 auth carrier、TLS、admission、HTTP server 与 safe telemetry；不改 wire 语义 |
| Workflow/Execution/Process | ES-02 | 启停 runner/scanner、设置资源 guard、执行 closed recovery port；不直写状态 |
| Intake/source/clean/Gate/lifecycle | ES-03 | 提供 egress、sandbox、resource 与 retention policy；不接受 Candidate/Revision |
| DB/object/UoW/backup protocol | ES-04 | 配置路径、权限、排程、告警与 runbook；不绕过 persistence lane |
| registry/provider/OCR | ES-05 | secret、egress、dependency pin、process sandbox、concurrency 与 provider health；不换 binding |
| LS-RAG artifacts | ES-06 | 资源、retention、integrity 与 release fixtures；不改 schema/kernel |
| vector/retrieval | ES-07 | 实测 exact-search envelope、监控、cleanup schedule、semantic gate；不公开 vector |
| runtime config/secret/health/telemetry | ES-08 | 唯一 operational owner；只产生 typed operational facts |
| business repair | 各来源 ES owner | ES-08 只能调用 closed owner repair port或指示创建既有 Task；无 generic update |

### 1.4 当前技术与安全证据

| Evidence | 可采用事实 | V1 决策 |
|---|---|---|
| Python 3.12 asyncio/signal docs | event loop、subprocess、signal 与 bounded shutdown 可由同一 Python process 协调 | 一个长期 Python process，SIGTERM drain；subprocess始终 adapter-scoped |
| Uvicorn deployment docs | workers/reload 会创建额外 process；programmatic single worker可控 | `workers=1`、`reload=false`，不使用 Gunicorn/multiprocess manager |
| Docker official security/build docs | non-root、capability reduction、immutable digest、small/pinned image降低风险 | OCI image digest pin、non-root、read-only rootfs、drop capabilities、SBOM/provenance |
| Playwright Python Docker docs | untrusted browsing应使用独立非 root user、Chromium sandbox与受控 seccomp | browser sandbox必须开启；不以 root 或 `--no-sandbox` 抓取网页 |
| OWASP SSRF guidance | URL/redirect/DNS/IP必须验证，应用层与网络层应同时限制 | public-IP validation、redirect revalidation、scheme/port限缩、network deny-by-default |
| Gemini official docs | generation/embedding走固定 Google API host与 exact model contract | Gemini egress只允许 `generativelanguage.googleapis.com:443`，不接受 caller endpoint |

技术参考：

- https://docs.python.org/3.12/library/asyncio.html
- https://www.uvicorn.org/deployment/
- https://docs.docker.com/engine/security/
- https://docs.docker.com/build/building/best-practices/
- https://playwright.dev/python/docs/docker
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- https://ai.google.dev/gemini-api/docs/embeddings

---

## 2. Scope / Non-scope

### 2.1 Scope

ES-08 只负责：

1. 一个 OCI image / 一个 release digest / 一个长期 MKB Python process 的部署拓扑；
2. strict runtime config、build/dependency manifest、secret file resolver 与 restart-only change；
3. internal TLS、simple Bearer token、Host/CORS/header/body/rate/concurrency admission；
4. HTTP/API/browser/provider egress、SSRF、redirect、DNS、path、archive 与 subprocess sandbox；
5. startup、readiness、liveness、graceful shutdown、crash reopen 与 background-loop supervision；
6. structured log、trace、closed metric catalog、alert condition 与敏感信息最小化；
7. local finite CLI、operational evidence ledger、backup/restore/recovery/cleanup runbook；
8. retention schedule、disk/capacity high-water 与 fail-closed growth gate；
9. target hardware 上的 measured safe operating envelope；
10. 汇总 ES-01..08、semantic benchmark、安全、fault、backup/restore 与零 legacy 依赖的 release gate。

### 2.2 Non-scope

- 不建设第二服务、独立 worker、queue broker、database/object/vector service、sidecar 或 control plane；
- 不建设 Kubernetes operator、通用 scheduler、运维 UI、远程 shell、generic admin/operator API、SQL console 或 object browser；
- 不增加 user、membership、RBAC、session、API key marketplace、Team-scoped token 或 per-user audit；
- 不增加 callback/webhook、push result、final answer、agent、Workflow authoring、source kind、request intent 或 raw vector surface；
- 不支持多副本、active-active、HA、跨区、remote DB、cloud object store、online migration、zero-downtime upgrade 或 live embedding-space cutover；
- 不支持任意 config plugin、dynamic provider、arbitrary command、arbitrary egress proxy、caller URL header/method 或 caller secret；
- 不以 metric threshold、reference hardware、benchmark throughput、backup interval或technical timeout形成 Owner SLA；
- 不把 compromised host/kernel/root、上游 token 保管、企业 PKI/KMS/防火墙产品或业务数据分类平台变成 MKB 产品责任；
- 不提供 legacy schema/data/config/runtime/API/queue/storage 的 migration、compatibility、dual-read 或 import；
- 不从 log、trace、metric、health、operation outcome、backup manifest或容器状态推导业务成功。

### 2.3 完成定义

ES-08的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现、硬件或真实provider上运行。任何实现要声明符合ES-08-v1.0并获得release promotion，必须同时满足：

1. release artifact只有一个 MKB image与一个长期 Python application process；
2. build、dependency、registry、Workflow、schema、config和secret refs均 exact、可复现、无 hot drift；
3. token、Team isolation、TLS、SSRF、path、browser、secret、log disclosure 的正负测试全部通过；
4. startup、readiness、shutdown、SIGKILL、DB busy/corrupt、lost wake与provider outage收敛且不假成功；
5. backup可从empty target完整恢复并通过全量 truth/vector/object/semantic validation；
6. 三张 operational tables 与 named UoW 登记到 ES-04 physical manifest；
7. retention与cleanup不破坏Task/lineage/proof/current/serving/active index或open Gate；
8. target hardware实测值不超过各上游provisional ceiling，并保留至少20%资源headroom；
9. ES-01..07全部622项HARD acceptance与本文件100项HARD acceptance有一一证据；
10. release evidence证明4份Owner Truth、8份Execution Spec、六StateFamily、113张owner tables + 13张infrastructure tables = 126张project-owned physical tables和零legacy runtime dependency完全闭合。

### 2.4 核心术语与 threat model

| Term | Exact meaning |
|---|---|
| Release unit | 一个 content-addressed OCI image及其签名、SBOM、provenance、registry/schema/Workflow bundle；不是微服务集合 |
| Runtime config | strict、versioned、restart-bound、无secret value的有效配置快照 |
| Secret slot | code/config-owned logical ref 到 read-only file 的有限映射；caller永不提供path/value |
| Readiness | 当前实例是否允许正常业务 admission 的operational projection；不是StateFamily或业务success |
| Liveness | event loop仍能响应且未永久卡死；不声明DB/provider/business健康 |
| Operational run | 一个有限CLI/serve/release动作的reservation、step evidence与terminal outcome事实；不是Task/Execution |
| Safe envelope | 在exact build、hardware、data profile和test workload下测得并配置的hard guard；不是服务承诺 |
| Security event | bounded code/metric/evidence；不是Incident产品或业务状态 |

Threat actors/inputs：持有效 token 但可能有 bug 的 internal orchestrator、不可信文档/网页/API/PDF、恶意 URL/redirect/DNS、异常 provider 输出、stale worker、误操作 operator、受污染 dependency/image。受保护资产：canonical truth、Team 隔离、secret、provider quota、object/vector bytes、availability和audit lineage。

明确 residual：如果 host kernel/root、container runtime、企业 secret mount或构建签名私钥已被攻陷，MKB 单体无法建立独立可信根；部署必须停机、轮换并从已验证发布物/备份重建，不能在应用内伪造“已安全”。

---

## 3. Scope Impact Audit

~~~text
Scope Impact Audit
- New product responsibility: no
- New externally visible product behavior: no; only required deployment probes and existing Contract protection
- New V1 capability: no
- New request intent/source kind/Workflow/Process capability: no
- New domain identity or StateFamily: no; operational run is a bounded factual ledger
- New deployment/runtime unit: no
- New database/backend: no
- New owner-truth file: no
- New execution-spec file: no; this is the fixed ES-08 slot
- Raises a fixed capacity ceiling: no
- Can be solved inside an existing file and boundary: yes
- Classification: no expansion
~~~

三张 operational tables只保存启动、迁移、备份、恢复、cleanup与release验证的typed evidence，关闭“失败只在日志”和“operator直接改库”两个盲点。它们没有public CRUD、业务lifecycle、任意operation kind、Team权限或新服务。OCI、TLS、CLI、health、metrics、browser/OCR child process都是一个既有应用/发布单元的实现，不扩大Owner产品范围。

---

## 4. Architecture Decisions

### 4.1 单体 deployment topology

~~~text
private internal orchestrator
  ── HTTPS + Bearer token ──> one OCI container
                                 ├─ one long-lived CPython 3.12 process
                                 │    ├─ FastAPI/Uvicorn workers=1
                                 │    ├─ ES-02 runner/scanners
                                 │    ├─ ES-04 persistence lane
                                 │    ├─ provider/source adapters
                                 │    └─ health/telemetry/admission
                                 ├─ bounded adapter children
                                 │    ├─ Chromium process tree, max1
                                 │    └─ Tesseract process, max2
                                 ├─ /var/lib/mkb      persistent data
                                 ├─ /var/backups/mkb  separate protected volume
                                 ├─ /run/secrets/mkb  read-only secret mount
                                 └─ /tmp/mkb          bounded tmpfs
~~~

固定部署规则：

1. 一个 OCI image、一个 container、一个长期 MKB Python process；`uvicorn workers=1`且`reload=false`。
2. Chromium/Tesseract是短生命周期adapter child，不监听端口、不持DB connection、不成为deployment unit；Python parent负责deadline、reap、terminate/kill和typed outcome。
3. embedded Turso仍由ES-04 single-process lock与persistence lane独占；CLI maintenance与`serve`不能同时持锁。
4. image以non-root UID/GID `10001:10001`运行；root filesystem read-only；只挂载四个明确目录。
5. drop all Linux capabilities、`no-new-privileges`、无host network/PID/IPC、无Docker socket、无device/host root mount；Chromium使用非root+sandbox+专用seccomp，不允许`SYS_ADMIN`或`--no-sandbox`。
6. `/dev/shm`为独立1 GiB tmpfs；`/tmp/mkb`为2 GiB、`nodev,nosuid` tmpfs；persistent data目录不执行内容。
7. image启动只执行`python -m mkb <closed-command>`；不含SSH、shell daemon、package manager runtime update或debug server。

容器不是Owner新增的服务。若部署环境不用OCI，也必须证明与本节相同的单进程、filesystem、identity、resource、network与release digest语义；V1规范发布物仍以OCI为唯一验收profile。

### 4.2 Runtime config 与 immutable binding

Production只接受一个 strict TOML 文件，schema=`mkb.runtime-config.v1`。bootstrap environment只允许：

| Env | Meaning |
|---|---|
| `MKB_CONFIG_FILE` | absolute regular-file path；默认`/etc/mkb/runtime.toml` |
| `MKB_SECRET_DIR` | absolute read-only directory；默认`/run/secrets/mkb` |

任何其他`MKB_*`环境变量、`.env`自动加载、CLI `--set key=value`、环境覆盖业务参数或provider SDK隐式proxy/key discovery均拒绝。Config解析规则：unknown key/type/enum/duplicate TOML key拒绝；所有duration/size/count有显式单位和上下限；path只允许本节固定mount下的relative child；禁止symlink、`..`、NUL和world-writable parent。

启动生成`EffectiveConfigManifestV1`：包含schema、exact effective values、secret logical refs、release/build/schema/registry/workflow digests和canonical SHA-256；不含secret value、secret content digest、absolute host path或token。相同release+config digest产生相同静态绑定；任何config/secret/dependency变化都必须replacement restart，不支持SIGHUP/hot reload。

运行中的Task/Execution/Invocation仍使用创建时exact binding。新config只改变新进程的operational guard，不能重绑定旧Workflow/model/Prompt/schema或重解释历史。

### 4.3 Secret slots、simple token 与 rotation

Secret目录只允许manifest登记的finite slot：

| Slot family | Cardinality | Usage |
|---|---:|---|
| `internal_token.current_digest` | exactly1 | SHA-256 of 32 random byte base64url Bearer token |
| `internal_token.previous_digest` | 0..1 | bounded rotation overlap，最多24h |
| `cursor_hmac.current` | exactly1 | ES-01 cursor HMAC |
| `cursor_hmac.previous` | 0..1 | 仅验证旧cursor，最多cursor TTL |
| `gemini.api_key` | exactly1 | ES-05 generation + ES-07 embedding |
| `tls.certificate` / `tls.private_key` | exactly1 each | in-process HTTPS |
| `source.<registered-ref>` | finite config manifest | ES-03 registered API credential/header material |

Resolver使用directory FD + `openat(O_NOFOLLOW)`；basename只能来自manifest，不能来自request/DB/payload。File必须regular、owned by runtime/approved secret group、mode `0400`或`0440`、size 1..16384 bytes、无NUL；只移除一个末尾LF。Secret value不得进入DB、message、object、config digest、log、trace、metric、exception、core dump或child argv；child需要credential时通过bounded inherited FD/pipe，调用后关闭。

Bearer token规则：

1. raw token为32 bytes CSPRNG后base64url-no-padding，wire长度43；其他长度/字符直接invalid。
2. MKB只读取token SHA-256 digest secret file，以constant-time compare对current/previous验证；不存raw token或caller identity。
3. 任一valid token拥有同一全局internal calling authority；`team_uuid`只寻址/隔离，不从token claim推导。
4. previous slot必须有`accept_until`且不超过config activation后24h；过期后即使文件仍在也拒绝。
5. normal rotation：外部生成new token/digest → config把old移到previous → replacement restart → caller切换 → 24h内移除previous并restart。
6. compromise rotation：不设overlap，立即移除旧digest、替换Gemini/source/TLS相关secret并restart；无法证明安全时停服务。
7. source/Gemini/TLS secret文件在进程运行中被替换或内容变化时，resolver与boot metadata不一致，相关调用fail-closed并使secret-integrity check not-ready；不得hot switch。

Rotation是配置事实，不是credential平台、token identity或StateFamily。V1不提供token签发/列举/撤销HTTP API。

### 4.4 Ingress、TLS、auth 与 anti-abuse

MKB container监听`0.0.0.0:8443`，但host/network policy只向已登记internal orchestrator CIDR开放。TLS在MKB进程内终结，最低TLS 1.2、优先TLS 1.3；证书/私钥来自secret slot。明文HTTP、public internet bind、Unix debug socket与fallback certificate均禁止。

业务请求顺序固定：

~~~text
TLS + Host + request-target/header framing validation
  → peer/global pre-auth abuse guard
  → exact Bearer parse + constant-time validation
  → global readiness/admission gate
  → strict content-type/body streaming budget
  → route schema + path/body UUID equality
  → Team lookup/active/data-scope guard
  → ES-01 application service
~~~

安全规则：

- Host必须在最多16项exact allowlist；不信任`X-Forwarded-*`，V1没有proxy mode。
- 无CORS、cookie、session、form、WebSocket、HTTP/2 cleartext或browser credential flow；OPTIONS不开放业务capability。
- reject `Content-Length`+`Transfer-Encoding`、duplicate auth/host/content-length、obs-fold、absolute-form target、invalid UTF-8 header和header总量>16 KiB。
- JSON route只接受`application/json`；body streaming hard max8 MiB，超限立即停止并413；inline content仍max1 MiB。
- auth在任何Team/Task/Intake/Artifact/Vector lookup前完成；wrong-Team保持ES-01 anti-enumeration。
- response统一`Cache-Control: no-store`、`X-Content-Type-Options: nosniff`；HTTPS加HSTS；error只返回safe code/request/trace。
- mutation replay由ES-01 command UUID/fingerprint/CAS处理；Bearer replay风险由TLS、private network、rotation和rate guard限制，不新增per-request nonce/session。

Token bucket只做进程内admission，不是计费/配额/Truth，restart可重置：pre-auth peer 5 req/s burst10；valid token全局50 req/s burst100；每Team read20/s burst40、mutation5/s burst10、retrieval2/s burst4。超限429+bounded `Retry-After`；bucket key只用token slot id/Team UUID，不进入产品schema。

### 4.5 Egress、SSRF 与 untrusted execution

所有network client必须使用`SafeEgressTransportPort`，SDK/browser不得自行解析或连接URL。Policy只有三类：

| Policy | Target |
|---|---|
| `gemini-google-v1` | exact `https://generativelanguage.googleapis.com:443` |
| `registered-api-v1` | SourceDefinition登记的exact HTTPS host/port/path prefix/method/header slots |
| `public-document-v1` | caller提供的http_resource；仅HTTPS、public-routable target、GET/HEAD |

每个initial/redirect/subresource request都执行：strict RFC URL parse → scheme/port/userinfo/fragment/header check → IDNA canonical host → A+AAAA resolve → normalize IPv4/IPv6/mapped address → 要求每个candidate address均为global unicast → connect到validated address同时保持TLS SNI/Host → response stream budget。禁止loopback、private、link-local、carrier-grade NAT、multicast、unspecified、reserved、documentation、metadata address；禁止`file/data/ftp/gopher/ws/wss`、custom proxy和SDK `trust_env`。

Redirect最多5次且每跳完整重验；跨origin不转发Authorization/cookie/source secret；registered API跨allowlist origin直接拒绝。DNS结果只在单次请求bounded TTL内使用，connect不得再次隐式解析；失败不能fallback到未验证address。Network firewall同时default-deny，只开放DNS、configured HTTPS egress和必要time sync；应用层通过不替代网络层证据。

Browser profile固定：Playwright+bundled Chromium exact pair、headless、non-root、sandbox on；一个ephemeral context/request，max120s、64 requests、16 distinct origins、64 MiB network、256 MiB decompressed、5 redirects。每个browser request仍经public-document policy；禁止download、popup、extension、DevTools、file access、WebRTC、WebSocket、service worker、persistent cookie/cache/profile和credential store。JS可以渲染内容，但不能改变MKB route/authority或读取secret。

Archive/PDF/XML/HTML规则：nested archive禁用、decompression ratio≤100:1、decompressed≤256 MiB；XML external entity/network resolution关闭；path extraction只用generated temp name；PDF parser/OCR/browser在deadline、memory、page/pixel budget内运行。Child timeout先TERM，5秒后KILL；partial output不成为Artifact/Outcome success。

### 4.6 Admission、concurrency 与 resource isolation

所有queue/semaphore都有hard bound，达到上限只backpressure/429/503，不创建隐式work或新服务：

| Resource | V1 ceiling before measurement | Overflow behavior |
|---|---:|---|
| admitted HTTP requests | 32 active + 64 wait | queue deadline后503 |
| mutation handlers / Team | 4 | 429/503，无DB side effect |
| persistence lane queue | 256 | pre-transaction 503 |
| outbox claim batch | 64 | remaining rows next scan |
| Process runner active | 8 | ready rows remainTruth |
| Gemini calls | global4 / Team2 / Process1 | ES-02 bounded wait/retry |
| OCR children | 2 | resource-transient outcome |
| Chromium context | 1 | resource-transient outcome |
| retrieval | global4 / Team2 | 503 busy；deadline10s |
| object streaming | 4 | bounded wait；no partial success |
| `/tmp/mkb` | 2 GiB | producer fail/cleanup，不spill rootfs |
| process PID | 512 | release/deployment failure if exceeded |

ES-03/05/07 的更低route/model/vector limit继续优先。Task priority只影响ES-02既有runner order，不越过security/concurrency hard guard。Limiter不持有业务状态；crash后由owner truth/scanner恢复。

Disk guard每5秒采样data/backup/tmp：usage≥80% warning；≥90%或free<2 GiB停止新mutation/build并令readiness false；≥95%停止全部非验证/backup/recovery I/O。不得自动删除canonical rows、old serving、current artifacts或backup last-two来“恢复健康”。

### 4.7 Startup、health 与 readiness

`serve`永不自动migration、restore、registry semantic upgrade或业务repair。Startup gate按§6.3运行，只有全部required check通过才接业务流量。

Operational routes：

| Route | Auth | Exact semantics |
|---|---|---|
| `GET /livez` | none，private network only | event loop最近5秒有tick且process未进入fatal-stop；200/503，绝不检查业务成功 |
| `GET /readyz` | none，private network only | exact readiness snapshot为ready且admission open；200/503，只返回coarse code |
| `GET /internal/metrics` | same valid Bearer token | closed Prometheus text catalog；无Team/resource/query高基数或secret |

成功body分别固定为`{"status":"live"}`与`{"status":"ready"}`；失败为`{"status":"not_live|not_ready","code":"bounded-safe-code"}`。不返回schema head、registry key、path、disk layout、provider、stack、secret或resource identity。

Required readiness checks：build/config/secret metadata、single-process lock、DB capability/quick_check/FK、exact migration/schema manifest、registry/Workflow/handler closure、object-root identity/reference integrity、active embedding space/vector function、serving/index pointer closure、background-loop heartbeat、disk/backup age与clock sanity。任一drift/corruption/mixed-space/missing live object使readiness false。

Gemini或某个外部source临时不可达不改变global readiness，因为startup不发external canary且old serving/polling仍可工作；对应call按ES-03/05/07返回typed retryable failure/503并触发dependency metric。Provider credential missing/changed、adapter/manifest不匹配则是local configuration failure，readiness false。

Readiness每5秒重算cheap checks；full pointer/object/reference scan在startup、restore、release和每24小时运行。Check结果是typed projection/operation evidence，不是StateFamily。Readiness false不自动fail/cancel Task；停止新admission/claim后由既有lease/recovery规则收敛。

### 4.8 Graceful shutdown 与 crash

SIGTERM/SIGINT顺序固定：

~~~text
set readiness false + close new admission
  → stop new outbox/Process/recovery/cleanup claims
  → drain accepted synchronous requests, max10s
  → finish current DB UoW/object promotion, total max30s
  → wait bounded provider/browser/OCR calls until remaining shutdown budget
  → TERM child; after5s KILL
  → flush typed telemetry
  → close persistence lane/checkpoint as ES-04 allows
  → release process lock and exit0 if clean
~~~

Container termination grace为45秒。超出时进程退出非零；不得延长为无界等待。被终止的provider call若结果/计费未知，next startup按ES-05/07 reservation deadline写`indeterminate`并由ES-02决定retry；不能把shutdown当failed或success Outcome。

SIGKILL/OOM/power loss没有shutdown truth。下次启动依赖WAL、single-process lock、missing-outcome scan、expired lease/fence、outbox scanner、object reservation与operation run recovery收敛。禁止从最后一条log猜commit或补terminal status。

### 4.9 Observability、trace、metrics 与 alerts

Production log只写单行canonical JSON到stdout/stderr，schema=`mkb.telemetry-event.v1`：

~~~text
occurred_at, severity, event_key, event_version
release_build_digest_prefix, instance_boot_uuid
request_uuid, trace_uuid, correlation_uuid, causation_uuid nullable
team_uuid, task_uuid, execution_uuid, process_uuid nullable by event
operation_run_uuid nullable
route_template/process_key/operation_kind bounded
outcome_class, safe_code, duration_ms, retryable
bounded numeric fields + payload_extra_safe
~~~

允许UUID只作内部correlation field，绝不作metric label。禁止body、query/filter原文、source URL query/userinfo、header、Bearer、secret ref value、prompt/model input/output、extracted text、artifact bytes、vector、SQL、driver row、absolute path、raw exception或unbounded provider response。Exception只记录allowlisted class、safe code和stack fingerprint；debug mode不存在production配置。

Trace规则：HTTP生成/接受ES-01 request ID后创建trace context；Task沿既有`trace_uuid`，outbox携带correlation/causation；provider/browser/OCR span只存binding/operation key与safe timing，不存content。Log/trace丢失不影响Truth，业务failure必须已有typed error/outcome/event或可重建owner fact。

Closed metrics见§5.9。Label值只能来自finite enum/route template/process key/model key/status family/HTTP class；禁止Team/Task/URL/digest/error message。Runtime每10秒更新in-memory metric；Prometheus scrape只是观测，不入业务DB。

最低alert条件：

| Severity | Condition | Required response |
|---|---|---|
| P0 | DB quick_check/FK失败、live object/vector payload missing/corrupt、cross-Team guard failure、secret disclosure detector、dual pointer inconsistency | readiness false、停止写、preserve evidence、按§6.9恢复 |
| P1 | dead-letter>0、ready Process/outbox oldest>5m、disk≥90%、backup age>72h、repeated child crash、schema/registry drift | admission closed或affected path fenced；operator runbook |
| P2 | provider consecutive failure≥5、outbox oldest>60s、disk≥80%、backup age>24h、rate/concurrency sustained | investigate/measure；不改业务truth |

P0/P1/P2是operator severity，不是StateFamily、Task priority或产品SLA。

### 4.10 Release、dependency 与 supply-chain gate

Release artifact必须包含并相互digest绑定：

1. source tree/commit digest；
2. Python 3.12 exact patch与base image digest；
3. hash-locked Python dependencies；
4. pinned OS packages、Tesseract 5.5.2、Playwright/Chromium exact pair；
5. pyturso、Google GenAI SDK与schema validator exact pins；
6. schema migration manifest、ES-04 physical table manifest；
7. ES-02 Workflow、ES-03 source/semantic/action/preflight、ES-05 registry、ES-06 StructureSchema与ES-07 space/policy bundles；
8. runtime config schema/template与closed metric/check/operation catalogs；
9. SPDX或CycloneDX SBOM、build provenance与OCI signature；
10. `ReleaseEvidenceManifestV1`及全部722项HARD evidence digest。

Build为multi-stage，runtime不含compiler/cache/test credential/package index config。Base image与download按digest pin；build secret不用`ARG/ENV/COPY`进入layer。任何Critical/known-exploited dependency finding必须修复或以可复现evidence证明not-present/not-reachable；不能用忽略规则或过期waiver把release标绿。

Release validation必须在fresh empty DB和upgrade-from-last-MKB-version两条路径运行；从不读取legacy data。Provider live canary只在隔离release环境执行一次exact generation与embedding contract，不在production startup执行。Semantic gate固定复用ES-07的16-document/32-query corpus与指标。

### 4.11 Maintenance、backup 与 restore

Operator只使用同一image的closed CLI。Maintenance command必须先取得ES-04 exclusive process lock；`serve`运行时命令失败，不提供remote maintenance endpoint。Host scheduler最多每24小时执行：停止container → same-image `backup` → 验证成功 → restart；这是部署编排，不是第二MKB服务。

Backup：

- exact ES-04 quiesced protocol；目标为独立、encrypted-at-rest、operator-only local volume；
- bootstrap后、首次serve前必须有一个verified backup；之后success gap≤24h，>72h readiness false；
- migration、registry/schema upgrade、embedding-space cutover前强制new verified backup；
- 保留最近7个verified full backup，永不删除最后2个；先完整验证new backup再删最旧；
- `.tmp`、missing manifest、digest/FK/object closure失败永不计入backup set；
- backup不对caller公开，不成为raw vector/object export。

Restore：

1. `serve`停止，target必须empty且位于new data root；
2. 校验image/schema compatibility、manifest签名/digest、DB、FK、所有live/held object/vector payload；
3. restore到temporary root，full validate + semantic smoke；
4. atomic deployment config切到new root并replacement start；
5. old root只读隔离，operator确认后按外部retention删除；禁止merge/原位覆盖。

每个release必须完成一次isolated restore drill；运行部署每90天完成一次。时长是runbook cadence，不是用户RTO/RPO承诺。

### 4.12 Retention 与 bounded cleanup

Retention只删除明确可丢的physical/detail substrate，绝不改变business lifecycle或public history：

| Class | V1 policy | Guard |
|---|---|---|
| Team/Task/Audit/Restart/Execution summaries、Intake canonical rows、decisions/transitions/proofs、registry definitions、LS-RAG/vector metadata skeleton | deployment lifetime；无自动hard delete | Owner history/lineage |
| terminal Process detail | 90 days后可删 | ES-02 cleanup eligible+summary digest+no pointer/lease/outbox/hold；before/after projection等价 |
| retrieval_query_receipts/hits | 30 days | no active incident/hold；按Team bounded batch；不含query/body |
| delivered outbox + matching inbox | 30 days after both terminal | business effect/event/proof已存在；dead-letter未解决不得删 |
| domain_events、Invocation skeleton、Publication/cleanup proof | deployment lifetime | audit/causation |
| raw invalid model/LS-RAG evidence bytes | 7 days | terminal invalid、no current/serving/history/hold required ref；保留digest/summary skeleton |
| old/nonactive vector payload | 24h minimum grace | ES-07 full eligibility+hold/reference proof；只删payload row |
| promoted object orphan | 24h minimum grace | ES-04无live ref/hold/reservation fence |
| temp files/abandoned child workspace | 1h | no live PID/reservation；startup sweep也遵守 |
| structured logs | 14 days或2 GiB，先到者 | container log rotation；不是truth |
| verified backup | latest7，minimum2 | new verified before old delete |
| open Gate evidence | indefinite | no auto-approve/expire；reference fence |
| operational runs/steps/outcomes | deployment lifetime；无自动hard delete | release/backup/restore/recovery/validation/cleanup证据均保持immutable |

Cleanup由bounded batches执行，每批写operational step digest/count并走owner UoW。Unknown eligibility、scan中变化、CAS 0 row、missing proof、backup in progress或disk emergency均fail-closed。Disk pressure不能缩短grace或删除last backup/current/serving/canonical truth。

---

## 5. Contracts and Data

### 5.1 Schema composition 与 physical profile

ES-08新增恰好3张global operational owner tables：

~~~text
operational_runs
operational_run_steps
operational_run_outcomes
~~~

它们遵守ES-04 UUIDv7、UTC、SHA-256、canonical JSON、STRICT、`ON DELETE RESTRICT`、immutable evidence与`payload_extra NOT NULL DEFAULT '{}'`规则。没有`status`列；operation的当前事实只由reservation、ordered step和0..1 terminal outcome推导。

加上本文件后：ES-01 4 + ES-02 9 + ES-03 34 + ES-05 18 + ES-06 21 + ES-07 24 + ES-08 3 = 113张owner tables；ES-04另有13张infrastructure tables，总计126张project-owned physical tables。Engine catalog不计入。

### 5.2 `RuntimeConfigV1`

Top-level exact sections：

| Section | Required typed fields |
|---|---|
| `meta` | schema_version、deployment_ref、activated_at、config_revision、expected_release_build_digest |
| `server` | bind_host=`0.0.0.0`、port=8443、trusted_hosts、TLS slot refs、header/body/keepalive/request deadlines |
| `auth` | current/previous token digest refs、previous_accept_until、cursor key refs、token/rate profiles |
| `storage` | fixed data/backup/temp relative roots、database/object identities、disk thresholds、backup age |
| `runtime` | queue/concurrency/scanner/shutdown limits |
| `egress` | exact policy definitions、DNS/connect/redirect/response/browser budgets |
| `registry` | expected schema/Workflow/source/model/Prompt/Structure/vector bundle refs+digests |
| `observability` | log level=`INFO`、metric/check intervals、closed label catalog、rotation requirement |
| `retention` | §4.12 exact durations/batches |
| `release` | dependency lock、SBOM、provenance、acceptance evidence digests |

Config不能包含secret value、raw URL credential、arbitrary header、SQL、Python import/callable、filesystem path outside fixed roots、unknown process/model/provider、dynamic plugin或debug flag。`deployment_ref`只标识一套运维配置，不作为domain identity或授权凭证。

### 5.3 `SecretManifestV1` 与 resolver contracts

~~~text
schema_version = mkb.secret-manifest.v1
config_revision, activated_at
slots[{slot_key, file_basename, value_kind, required, max_bytes,
       allowed_consumers, previous_accept_until?}]
manifest_digest
~~~

`slot_key/file_basename/consumer`均来自closed schema；basename unique、无slash。Manifest只保存ref与policy；不保存secret content hash。Boot在memory中保存file identity+content fingerprint用于drift detection，既不持久化也不输出。

~~~python
class SecretResolverPort(Protocol):
    def resolve(self, request: SecretResolveRequestV1) -> SecretLeaseV1: ...
    def validate_boot_snapshot(self) -> SecretIntegrityReportV1: ...

class TokenVerifierPort(Protocol):
    def verify_bearer(self, authorization: str) -> InternalAuthorityV1: ...
~~~

`InternalAuthorityV1`只有`valid=true`、token slot generation与request correlation；没有user/role/Team claim。`SecretLeaseV1`不可序列化、repr或跨operation缓存，离开consumer scope立即关闭/清空best-effort。

### 5.4 Operational evidence tables

#### 5.4.1 `operational_runs`

~~~text
operational_run_uuid UUIDv7 PK
schema_version TEXT = mkb.operational-run.v1
operation_kind TEXT CHECK(
  serve_session|initialize|migrate|registry_install|validate|backup|restore|
  release_verify|recovery|secret_rotation|incident_response|retention_cleanup|integrity_scan|capacity_benchmark
)
command_version TEXT
command_uuid UUIDv4/v7
idempotency_key TEXT 1..200
request_digest TEXT(64 lower hex)
release_build_digest TEXT(64 lower hex)
dependency_lock_digest TEXT(64 lower hex)
effective_config_digest TEXT(64 lower hex)
schema_manifest_digest TEXT(64 lower hex) nullable only before DB-open validation
operator_actor_ref TEXT nullable only serve_session
previous_run_uuid UUID nullable FK operational_runs
input_manifest_kind TEXT nullable CHECK(release|backup|migration|cleanup|recovery)
input_manifest_digest TEXT nullable
started_at TEXT UTC
deadline_at TEXT UTC
payload_extra TEXT canonical object
UNIQUE(operation_kind, idempotency_key)
UNIQUE(command_uuid)
~~~

Same kind/key+same request digest返回original run；same key+different digest conflict。`operator_actor_ref`是local OS/deployment principal的salted safe ref，不建立MKB RBAC。Row immutable。

#### 5.4.2 `operational_run_steps`

~~~text
operational_run_uuid UUID FK operational_runs
step_ordinal INTEGER >=0
schema_version TEXT = mkb.operational-run-step.v1
step_key TEXT from closed catalog
step_version TEXT
step_disposition TEXT CHECK(passed|failed|warning|not_applicable)
finding_code TEXT nullable from closed safe catalog
evidence_kind TEXT CHECK(inline_digest|release_bundle|backup_manifest|runtime_probe|owner_receipt)
evidence_digest TEXT(64 lower hex)
evidence_size_bytes INTEGER >=0
started_at, completed_at TEXT UTC
duration_ms INTEGER >=0
payload_extra TEXT canonical object
PK(operational_run_uuid, step_ordinal)
UNIQUE(operational_run_uuid, step_key)
~~~

Step append-only。Required step不得`not_applicable`；warning只允许catalog标明non-blocking的backup-age/provider-observation类，不能降级HARD acceptance、integrity、security或schema failure。

#### 5.4.3 `operational_run_outcomes`

~~~text
operational_run_uuid UUID PK/FK operational_runs
schema_version TEXT = mkb.operational-run-outcome.v1
outcome_kind TEXT CHECK(succeeded|failed|indeterminate)
outcome_code TEXT from closed safe catalog
step_count INTEGER >=0
step_set_digest TEXT(64 lower hex)
evidence_manifest_kind TEXT CHECK(release|backup|restore|validation|recovery|cleanup|serve)
evidence_manifest_digest TEXT(64 lower hex)
exit_code INTEGER
completed_at TEXT UTC
payload_extra TEXT canonical object
UNIQUE(operational_run_uuid, evidence_manifest_digest)
~~~

Outcome immutable且每run最多一个。`succeeded`要求全部required step passed、step count/digest闭合；failed要求至少一个blocking finding；indeterminate只用于process crash/commit ambiguity且由后续exclusive-lock recovery证明前实例不再运行。Outcome不改变Task/Execution/Process/Item或readiness Truth。

### 5.5 Application ports

~~~python
class RuntimeConfigPort(Protocol):
    def load_exact(self) -> EffectiveConfigManifestV1: ...
    def validate_drift(self) -> ConfigIntegrityReportV1: ...

class SecretPolicyPort(Protocol):
    def resolve_slot(self, request: SecretResolveRequestV1) -> SecretLeaseV1: ...
    def resolve_egress_policy(self, ref: EgressPolicyRefV1) -> EgressPolicyV1: ...

class ReviewAuthorityPort(Protocol):
    def authorize_gate_decision(self, auth: InternalAuthorityV1, evidence: ReviewActorEvidenceV1) -> ReviewAuthorityReceiptV1: ...

class AdmissionPort(Protocol):
    async def admit(self, request: AdmissionRequestV1) -> AdmissionLeaseV1: ...

class SafeEgressTransportPort(Protocol):
    async def execute(self, request: EgressRequestV1) -> VerifiedEgressStreamV1: ...

class BrowserSandboxPort(Protocol):
    async def render_once(self, request: BrowserRenderRequestV1) -> BrowserRenderOutcomeV1: ...

class HealthPort(Protocol):
    def liveness(self) -> LivenessSnapshotV1: ...
    def readiness(self) -> ReadinessSnapshotV1: ...

class TelemetryPort(Protocol):
    def emit(self, event: TelemetryEventV1) -> None: ...
    def observe(self, metric: MetricObservationV1) -> None: ...

class OperationalRunPort(Protocol):
    async def reserve(self, command: OperationalRunCommandV1) -> OperationalRunV1: ...
    async def append_step(self, result: OperationalStepResultV1) -> OperationalRunV1: ...
    async def complete(self, outcome: OperationalRunOutcomeDraftV1) -> OperationalRunOutcomeV1: ...

class ReleaseGatePort(Protocol):
    async def verify(self, manifest: ReleaseEvidenceManifestV1) -> ReleaseGateResultV1: ...

class ShutdownCoordinatorPort(Protocol):
    async def drain(self, reason: ShutdownReasonV1) -> ShutdownReceiptV1: ...
~~~

不存在generic command runner、raw subprocess、raw socket、raw secret、raw metric label、generic repair、SQL/path/object/vector debug port。

`SecretPolicyPort`是ES-03所见的组合边界：slot仍由本文件resolver拥有，egress policy仍是closed config definition。`ReviewAuthorityPort`只验证已有`InternalAuthorityV1.valid`与bounded actor evidence shape，并回传`authority_kind=global_internal_token`；它不查询user/member/role，不把actor evidence变成权限，也不允许跨Team resource lookup绕过ES-01/03 guard。

### 5.6 Internal protocol schemas

#### 5.6.1 `EgressRequestV1`

~~~text
policy_ref + policy_digest
purpose CHECK(source_static|source_browser|registered_api|gemini_generation|gemini_embedding)
method from policy
canonical URL or provider operation ref
header slot refs, never header secret value
body logical ref/digest/size, never caller path
connect/read/total deadline
redirect/response/decompression/request budgets
team/task/execution/process/fence causation when Process-owned
trace/correlation/causation UUIDs
~~~

Response只有status/final canonical URI sans sensitive query、redirect evidence、verified media/size/digest、bounded stream completion与safe transport code。没有raw socket/IP列表、credential或unbounded headers。

#### 5.6.2 `ReadinessSnapshotV1`

~~~text
snapshot_at, boot_uuid, effective_config_digest
required_check_count, passed_count, blocking_count
check_set_digest
admission_open boolean
coarse_public_code
internal findings[{check_key, disposition, safe_code, evidence_digest}]
~~~

Public mapper只输出status+coarse code。Snapshot不持久化为business status；release/validate operation可以把digest和steps写operational ledger。

#### 5.6.3 `TelemetryEventV1`

Event严格匹配§4.9字段；`payload_extra_safe`只允许event catalog声明的标量key，单event编码≤16 KiB。Logger在serialize前递归secret/content/path/vector deny-scan；失败时丢弃unsafe fields并发`telemetry.redaction-failed.v1`安全计数，不能把原值写fallback log。

#### 5.6.4 `OperationalRunCommandV1`

~~~text
schema_version = mkb.operational-run-command.v1
operation_kind + command_version
command_uuid, idempotency_key, request_digest
release/dependency/config/schema manifest digests
operator_actor_ref
input manifest kind/ref/digest nullable by command
deadline_at
closed typed parameters by operation kind
~~~

Command不接受SQL、table、path outside fixed roots、URL、shell、Python callable、secret value、Task status或arbitrary JSON mutation。

#### 5.6.5 `ReleaseEvidenceManifestV1`

~~~text
schema_version = mkb.release-evidence.v1
release_build/image/source/dependency/SBOM/provenance/signature digests
schema/table/registry/workflow/config/metric/operation catalog digests
acceptance manifest: ES01..08 exact IDs, counts, result/evidence digests
state-family and owner-write audit digests
fresh/upgrade/bootstrap/fault/restore/security/legacy scan digests
semantic corpus/policy/result metric digests
reference hardware + measured envelope + effective ceilings
provider live-canary refs/digests without payload
created_at, toolchain digest, root_manifest_digest, signature_ref
~~~

Manifest不包含test corpus正文、query、vector、secret、absolute path、provider raw response或private signing key。

### 5.7 Closed CLI inventory

| Command | Exact authority/effect |
|---|---|
| `mkb serve` | read-only startup validation后运行HTTP/runner；no migration/repair |
| `mkb initialize --empty-target` | fresh target only；migrations+registry/Workflow bootstrap+validate |
| `mkb migrate --plan|--apply --expected-head` | maintenance lock；forward-only MKB migration |
| `mkb registry-install --expected-bundle-digest` | exact built-in bundle；same digest no-op |
| `mkb validate --level startup|full|release` | no business mutation；full可append operation evidence |
| `mkb backup --backup-id` | quiesced ES-04 protocol；ID generated/validated，非path |
| `mkb restore --backup-id --empty-target` | verified empty target only；不覆盖active root |
| `mkb cleanup --kind temp|orphan_object|process_detail|retrieval_evidence|delivery_ledger|vector_payload --dry-run|--apply` | closed eligibility + bounded batch + owner UoW |
| `mkb recover --kind operation_close|runtime_wake|outbox_redelivery|integrity_recheck --dry-run|--apply` | closed owner repair ports；无generic row edit |
| `mkb verify-release --manifest-id` | 722项gate + evidence outcome；不启动production serve |

所有mutation command要求exclusive lock、operator OS identity、typed confirmation digest与dry-run evidence；无interactive shell prompt依赖。Exit `0`只表示operation outcome succeeded，不代表Task或knowledge成功。

### 5.8 Operational HTTP contracts

`/livez`、`/readyz`、`/internal/metrics`不在`/v1` product OpenAPI capability inventory，不接受Team/path/query/body，不创建Task/Audit/Execution/Process/outbox。只支持GET；其他method 405且零side effect。

Metrics route使用与业务API相同valid/invalid token口径，不建立operator role。Invalid token先401且不暴露metric existence/detail；valid token可访问，是Owner冻结的“任一有效token拥有全部功能”的直接实现。若未来需要独立operator权限，属于foundational trust-model reopen，V1不预留第二套auth。

### 5.9 Closed metric catalog

| Metric family | Type | Allowed labels |
|---|---|---|
| `mkb_http_requests_total` / `duration_seconds` | counter/histogram | route_template、method、status_class、safe_code |
| `mkb_admission_rejected_total` | counter | guard_kind、safe_code |
| `mkb_task_projection` | gauge | request_intent、task_status |
| `mkb_process_projection` / `outcomes_total` | gauge/counter | process_key、process_status/outcome_kind |
| `mkb_process_retry_recovery_total` | counter | process_key、kind、safe_code |
| `mkb_outbox_pending` / `oldest_seconds` / `dead_letter_total` | gauge/counter | message_type、terminal_kind |
| `mkb_persistence_queue_depth` / `uow_seconds` / `busy_total` | gauge/histogram/counter | transaction_profile、result |
| `mkb_object_bytes` / `orphan_count` / `integrity_incidents` | gauge/counter | object_class、incident_kind |
| `mkb_inference_calls_total` / `duration_seconds` / `tokens_total` | counter/histogram | model_key、purpose、outcome_kind |
| `mkb_browser_ocr_runs_total` | counter | adapter_key、outcome_kind |
| `mkb_vector_memberships` / `payload_bytes` | gauge | space_key、eligibility_class |
| `mkb_retrieval_requests_total` / `duration_seconds` / `hits` | counter/histogram | outcome_class、empty_reason、policy_key |
| `mkb_readiness` / `readiness_check` | gauge | check_key、disposition |
| `mkb_disk_bytes` / `backup_age_seconds` | gauge | volume_class、usage_kind |
| `mkb_operational_runs_total` | counter | operation_kind、outcome_kind |
| `mkb_security_events_total` | counter | event_kind、safe_code |

Histogram buckets由metric catalog version固定，不能runtime注入。Token cost是usage projection，不是billing；unknown usage不写0。Metric scrape失败不改变业务truth。

### 5.10 Named transaction profiles

| Profile | Atomic effect | Guard |
|---|---|---|
| `operational_run_reserve_v1` | one operational_run | kind/key/request digest idempotency；exact build/config |
| `operational_step_append_v1` | next ordered immutable step | run无terminal outcome；ordinal+step unique |
| `operational_run_complete_v1` | one terminal outcome | required step closure + set digest |
| `process_detail_retention_v1` | eligible terminal Process rows delete + operation step | ES-02 cleanup fence、90d、summary equivalence |
| `retrieval_evidence_retention_v1` | bounded receipt/hit delete + operation step | 30d、no hold/incident、Team batch digest |
| `delivery_ledger_retention_v1` | delivered outbox/inbox delete + operation step | both terminal≥30d、business event/effect proof retained |

Object/vector cleanup继续使用ES-04/07既有`object_delete_proof_v1`、`vector_cleanup_finalize_v1`与owner cleanup profiles。Operational step只能记录已由owner UoW完成的effect，不能替代其proof。

---

## 6. State / Consistency / Failure

### 6.1 StateFamily boundary 与 factual automata

ES-08没有domain StateFamily。以下都由row/timestamp/presence推导，不增加generic status：

#### 6.1.1 Operational run facts

~~~text
no row
  ──reserve UoW──> immutable operational_run, no outcome
reserved
  ├──append exact next step──> ordered step facts
  ├──all required closure──> one succeeded|failed outcome
  └──previous process proven gone + ambiguity──> one indeterminate outcome

terminal outcome is immutable; no reopen/retry-in-place
new attempt = new run linked by previous_run_uuid
~~~

#### 6.1.2 Runtime readiness projection

~~~text
boot validation incomplete → admission closed
all required checks pass → admission open
blocking drift/failure/drain → admission closed
checks recover + exact revalidation → admission may reopen
~~~

这只是memory projection和typed check evidence；不存`booting/ready/degraded`业务status，不改变Task/Process。

#### 6.1.3 Token rotation facts

~~~text
current only
  → replacement config: new current + old previous(until <=24h)
  → replacement config: new current only

compromise: current old → replacement current new, no overlap
~~~

文件存在、metric或log都不能声明rotation成功；只有new process的config/secret validation与old token negative test构成evidence。

### 6.2 全局 invariants

1. 运行拓扑始终一个MKB release、一个长期Python process、一个DB owner lock。
2. Config/secret/build/schema/registry/Workflow exact digest不匹配时fail readiness，不hot repair或fallback。
3. 任一valid token权限完全相同；Team UUID永不成为credential或token claim。
4. Auth在resource lookup前；所有business reads/writes仍Team-scoped。
5. Egress只走closed policy；每个DNS result、redirect、browser subrequest都重新验证。
6. Secret value只在resolver→exact adapter内存/FD中出现，不进入持久化、telemetry或public response。
7. Health/log/metric/operation/backup不拥有任何六StateFamily transition或business success。
8. External call、browser/OCR、filesystem stream不在DB transaction内；DB UoW不执行它们。
9. Shutdown/crash不能制造terminal Outcome；missing/indeterminate按source ES规则恢复。
10. Operator没有raw SQL/path/object/vector/state mutation；所有repair经closed owner port/UoW。
11. Cleanup只有owner eligibility+retention+reference/hold/backup+CAS全部成立才执行。
12. Disk pressure、provider outage或backup failure不能删除old serving、current proof或放宽validation。
13. Restore只到empty target；通过full validation前不切换生产路径。
14. Release只在722项HARD evidence、semantic gate、security/fault/restore和scope audit全通过后promotion。
15. Benchmark guard只能降低/维持上游ceiling；提高必须new measured release evidence，永不自动扩服务。

### 6.3 Startup execution chain

~~~text
verify OCI/build/signature/dependency manifest
  → load strict config + secret manifest metadata
  → validate filesystem ownership/modes/mount identity/free space
  → acquire exclusive process lock
  → open ES-04 persistence lane and apply exact PRAGMAs
  → DB capability probe + quick_check + FK
  → require exact migration/schema/table manifest; no auto migrate
  → validate registry/source/action/preflight/model/prompt/schema bundles
  → compile/validate all 8 Workflow and 26 Process manifests
  → validate object root/live references and active vector space/function
  → validate serving/index dual pointer and semantic recovery invariants
  → recover expired previous serve operation/missing outcomes through owner ports
  → start bounded scanner/runner/telemetry loops
  → require loop heartbeat + backup age/disk guards
  → set admission open and /readyz 200
~~~

任一步失败：没有新business row/Task；readiness 503；记录safe typed failure/operation evidence（DB可用时）并退出或保持diagnostic liveness。无法打开DB时不自动创建替代空DB。

### 6.4 Request execution chain

~~~text
TLS framing/Host/header check
  → pre-auth limiter
  → constant-time token validation
  → readiness + global admission semaphore
  → content-type/body stream budget
  → strict route model
  → Team gate/data scope
  → ES-01/07 application port
  → typed response mapper + disclosure guard
  → bounded telemetry after response
~~~

Limiter、telemetry或response send失败不回滚已commit business effect。Mutation response丢失由idempotency replay；retrieval receipt由ES-07 atomic UoW；日志不得用来判断是否commit。

### 6.5 Source/provider egress chain

~~~text
Process/current fence + exact manifest
  → resolve policy + secret logical slots
  → reserve Invocation/object evidence when required
  → strict URL/operation canonicalization
  → DNS A/AAAA + global-address validation
  → connect validated address with TLS hostname verification
  → every redirect/subrequest repeats guard
  → stream bounded response; hash/count/media verify
  → close secret lease/network/browser context
  → persist bytes first, then typed Outcome via owner UoW
~~~

Policy reject是nonretryable input/security failure；DNS/timeout/5xx按manifest allowlist retryability；body/decompression/redirect overrun fail-loud。Partial network/browser output不进入Candidate/Artifact/Invocation success。

### 6.6 Shutdown/crash chain

Graceful shutdown遵守§4.8。关键race：

| Window | Durable truth | Recovery |
|---|---|---|
| request admitted before drain | maybe no/committed business effect | bounded finish；client replay by idempotency |
| DB UoW COMMIT unknown | maybe all committed | exact idempotency/readback，不盲重做 |
| provider sent, no outcome | invocation reservation | deadline+grace后indeterminate；new Process retry only |
| object promoted, ref UoW absent | orphan | owner resume或24h GC |
| Process claimed, no outcome | current lease/fence | expiry recovery，stale child fenced |
| outbox claimed, no ack | outbox lease | expiry/redelivery + inbox idempotency |
| browser/OCR child killed | no valid completion | typed transient/indeterminate，no Artifact success |
| operational run no outcome | reservation/steps | next exclusive owner writesindeterminate或exact completion evidence |

### 6.7 Operational command chain

~~~text
validate local OS authority + exclusive lock
  → canonical command + digest
  → operational_run_reserve_v1
  → execute only closed typed steps
  → each durable effect first commits through owner UoW
  → append step evidence digest/count
  → build canonical evidence manifest
  → operational_run_complete_v1
  → exit code derived from terminal outcome
~~~

Crash betweenowner effect与step append时，recovery以owner idempotency/effect proofreadback补同step；不能重复effect。Crash before effect只写indeterminate/failed step，不猜success。

### 6.8 Failure disposition matrix

| Failure | Readiness/admission | Business disposition | Operator action |
|---|---|---|---|
| invalid config/secret permission/drift | false | zero new work | replace exact config/secret + restart |
| TLS cert invalid/expiring critical | false | no plaintext fallback | rotate cert + restart |
| invalid token/rate abuse | unchanged | 401/429，zero lookup/effect | security metric/rotate if compromise |
| SSRF/path/archive/browser policy reject | affected request only | typed nonretryable failure | correct definition/input；no allow bypass |
| Gemini/source outage | global ready may remain | Process retry/failed or retrieval503；old serving remains | observe/retry budget，不换provider |
| DB busy transient | queue/backpressure | UoW retry/readback per ES-04 | reduce load/inspect disk |
| DB corruption/FK/schema drift | false，stop writes | no auto repair | backup+restore empty target |
| live object/vector missing/corrupt | false/P0 | affected read fail-closed | exact backup restore or existing rebuild Task |
| outbox lost wake/dead-letter | P1 if threshold | owner truth remains | closed redelivery/repair port |
| Process stranded/lease expired | affected growth guarded | ES-02 recovery | scanner/closed recover command |
| disk≥90%/backup stale>72h | false for admission | no cleanup shortcut | verified backup/eligible cleanup/capacity provision |
| OOM/SIGKILL | process dead | WAL/fence/reservation recovery | restart exact image; investigate envelope |
| semantic release regression | production unchanged | candidate release blocked | fix code/config/model policy; no threshold waiver |
| legacy dependency found | release blocked | no runtime promotion | remove dependency; do not build adapter |

### 6.9 Recovery runbooks

#### 6.9.1 Database/schema corruption

Stop serve → preserve DB/WAL/config/evidence read-only → run offline `validate` → choose newest fully verified compatible backup → restore empty target → full FK/object/vector/pointer/registry/semantic validation → replacement start。禁止`PRAGMA writable_schema`、manual SQL patch、new empty DB替换或merge。

#### 6.9.2 Missing/corrupt object or vector payload

Fence readiness/affected retrieval → verifylive reference/pointer → restore exact bytes only ifbackup digest/size matchessame object identity → otherwise use existing `intake.rebuild`/`index.rebuild` via orchestrator → full publication proof before pointer change。不得创建空bytes、改expected digest或从nearest file猜对象。

#### 6.9.3 Stranded runtime/outbox

Run dry scan → compare Task/Execution/Process/lease/outbox/inbox truth → call ES-02/04 closed recovery port → same identity/idempotency/fence repair missing wake or expire stale lease → repeat scan until fixed point。不得new fake Process、force Task success或重放non-idempotent external call under old Invocation。

#### 6.9.4 Secret compromise

Close ingress/egress → remove compromised token previous overlap → rotate related token/API/source/TLS secrets externally → replacement config/restart → negative old-secret tests + positive new-secret tests → inspect safe security/Invocation evidence → rebuild only ifdata integrity affected。Never log secret for comparison。

#### 6.9.5 Disk/capacity pressure

Stop growth → create/verify backup if space permits → dry-run only eligible §4.12 cleanup → provision larger same-profile local volume or lower admission ceilings → full validate → reopen。不得引入remote backend/shard/service或delete protected truth。

#### 6.9.6 Provider/browser/OCR failure

Keep exact binding → validate local manifest/secret/sandbox → allow ES-02 retry budget/new Invocation → if external outage wait；if pinned binary incompatible block release/affected capability。No fallback provider、no `--no-sandbox`、no silent deterministic/OCR/Vision substitution。

### 6.10 Concurrency、retention 与 backpressure consistency

- Limiter lease必须在request/adapter completion或cancel时finally释放；leak watchdog只修operational counter，不改Task。
- Scanner uses stable keyset + observed revision/fence; scan overlap不能duplicate Process/outbox/cleanup effect。
- Retention batch最大500 rows或64 MiB logical evidence，先到者；每batch独立UoW与step digest，避免长transaction。
- Process cleanup与poll race：poll只依赖Execution summary/proof；删除前后response canonical digest必须相同。
- Retrieval evidence cleanup与active request race：receipt UoW先完成；cutoff按completed_at且至少30d，不触碰in-flight reservation。
- Delivery ledger cleanup与redelivery race：只有delivered+matching inbox且terminal≥30d；active lease/dead-letter不eligible。
- Backup/cleanup互斥maintenance fence；cleanup不能改变正在enumerate的backup set。
- Configured ceiling lower thancompiled upstream max时admission按lower值；高于upstream max使startup fail。

### 6.11 Security residuals 与 disclosure

- Valid internal token本身是全局authority；MKB不阻止该caller访问任一Team，因此token必须只交给受信orchestrator。
- Hit正文可能敏感；caller已位于相同internal trust boundary。V1不增加document ACL/DLP平台。
- TLS/network policy无法抵御compromised host/root；备份和secret mount必须由deployment environment保护。
- Provider会收到manifest允许的最小content；MKB不能将外部provider变成本地信任域，release/deployment必须接受其数据处理条款。
- Metrics/health只在private network；metrics虽需token，仍不得含高基数identity或content。
- Security/recovery evidence只能说明observed controls，不可证明业务knowledge正确；semantic/grounding仍由ES-06/07 proof与benchmark裁决。

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy anchor/practice | Retain | Rewrite in ES-08 | Drop |
|---|---|---|---|
| Cloudflare Worker env/bindings | environment-specific config必要性 | one strict TOML + read-only secret slots + exact digest | implicit binding discovery、platform runtime dependency |
| D1/R2/queue operational coupling | durable data/wake/bytes都需观测 | embedded Turso + local CAS + outbox metrics/recovery | Cloudflare service、remote queue、callback success |
| console admin/debug routes | operator需诊断与恢复 | local closed CLI + safe metrics/health | UI、raw file/vector browse、SQL/debug endpoint |
| legacy fetch/browser helpers | real web/PDF/browser capability与redirect risk | central SafeEgressTransport + sandbox + budgets | arbitrary URL/header/method、Cloudflare bypass、`--no-sandbox` |
| legacy `console.log`/free-form errors | correlation价值 | typed bounded JSON events + closed metrics | body/token/provider response/stack-as-truth |
| process/purger force/reset | recovery与cleanup确有需要 | owner eligibility/UoW/proof + operational ledger | fake Process、force success、direct row reset、mixed purge |
| multiple legacy packages/workers | capability evidence | one Python package/release with internal modules | separate service topology、wire/schema/status compatibility |
| legacy env secrets | external credential injection | no-env secret file resolver, restart-only binding | DB/config/log secret、hot reload、caller path |

`legacy-family/`与`legacy-python/`不进入image build context、dependency lock、imports、config、fixtures、DDL、runtime path、protocol或acceptance oracle。Reference anchor只能出现在文档/traceability evidence中。

---

## 8. Acceptance Evidence

以下100项全部为HARD。实现任何失败都阻止conformance和release promotion；不存在owner waiver或“先上线后补”。

### 8.1 Topology、image 与 supply chain

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A001 | deployment inventory | 恰一个MKB OCI image/container/long-lived Python process；无sidecar/service |
| ES08-A002 | Uvicorn config inspection | workers=1、reload=false、无Gunicorn/multiprocess manager |
| ES08-A003 | DB ownership under serve/CLI concurrency | exclusive lock使第二owner失败；无双writer |
| ES08-A004 | container identity/mount scan | UID/GID10001、rootfs read-only、仅四个明确mount |
| ES08-A005 | capability/privilege scan | no-new-privileges、cap drop all、无host socket/device/root mount |
| ES08-A006 | child process inventory | 只有bounded Chromium/Tesseract child；无listener/DB connection/daemon |
| ES08-A007 | image reproducibility twice | source/lock/base digest相同产生相同declared artifact digests |
| ES08-A008 | SBOM/provenance/signature | exact image digest闭合且可验证；无secret layer |
| ES08-A009 | dependency vulnerability gate | Critical/known-exploited均resolved或可证not-present/not-reachable；无ignore waiver |
| ES08-A010 | runtime image content | 无compiler/test credential/package cache/SSH/debug server/legacy package |

### 8.2 Config、secret 与 rotation

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A011 | unknown/duplicate/wrong-type config | startup fail-loud，零business row |
| ES08-A012 | unapproved `MKB_*` env/`.env`/CLI override | rejected；effective config不漂移 |
| ES08-A013 | config canonicalization golden | same values same digest；secret value/path不在manifest |
| ES08-A014 | symlink/world-writable/outside-root config | startup拒绝 |
| ES08-A015 | secret symlink/type/mode/owner/size/NUL matrix | resolver逐项fail-closed且无value leak |
| ES08-A016 | secret value repo/DB/object/log/core scan | zero matches；child argv/env也无secret |
| ES08-A017 | token format/constant-time compare | 43-char valid；malformed/invalid统一401且时间无可利用分支 |
| ES08-A018 | two valid rotation slots | current/previous权限完全相同；不含Team/user claim |
| ES08-A019 | previous accept_until boundary | 到期立即拒绝；≤24h；current持续有效 |
| ES08-A020 | compromise rotation | old token/key negative、新secret positive、无overlap/hot reload |

### 8.3 Ingress、auth、Team isolation 与 limits

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A021 | plaintext/public ingress attempt | no business listener/fallback；HTTPS private policy only |
| ES08-A022 | invalid Host/forwarded header | reject；不信任proxy identity |
| ES08-A023 | CL+TE/duplicate critical/oversized header | connection/request rejected，zero app effect |
| ES08-A024 | missing/invalid token probing known/unknown Team | lookup前同401；无existence leak |
| ES08-A025 | valid token across two registered Teams | 均可调用；data仍按path Team隔离，无RBAC gate |
| ES08-A026 | wrong-Team Task/Item/Artifact/retrieval | 404/empty安全语义；无cross-Team content/existence |
| ES08-A027 | content-type/body 8MiB+1 | 415/413 streaming stop；无read-all/Task row |
| ES08-A028 | token/Team/mutation/retrieval rate buckets | 429+Retry-After；restart reset不改变Truth |
| ES08-A029 | global/request queue saturation | bounded 503；queue不超64、无orphan business work |
| ES08-A030 | response/security disclosure scan | no secret/stack/SQL/path/driver/runtime/vector/model/final answer |

### 8.4 Egress、SSRF、browser 与 content safety

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A031 | scheme/userinfo/fragment/port/proxy abuse | reject non-HTTPS、userinfo、unsupported port/proxy |
| ES08-A032 | IPv4/IPv6/mapped private/link-local/metadata corpus | all rejected before connect |
| ES08-A033 | DNS answer mixed public/private | entire target rejected；不挑public fallback |
| ES08-A034 | DNS rebinding between resolve/connect | pinned validated address；no implicit second resolve |
| ES08-A035 | redirect to private/cross-credential origin | each hop revalidated；credential stripped/reject |
| ES08-A036 | registered API host/path/method/header escape | rejected；secret只到exact allowlisted origin |
| ES08-A037 | Gemini SDK endpoint/proxy override | only fixed Google host:443；caller/config不可替换 |
| ES08-A038 | Chromium sandbox inspection | non-root+sandbox+seccomp；`--no-sandbox`/SYS_ADMIN release fail |
| ES08-A039 | browser popup/download/ws/webrtc/service-worker/file request | blocked；ephemeral context清除 |
| ES08-A040 | archive/XML/PDF/browser budget bombs | bounded termination；no partial Artifact/Outcome success |

### 8.5 Startup、health、shutdown 与 crash

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A041 | fresh initialized startup | exact check chain后才ready；no provider startup call |
| ES08-A042 | serve against unmigrated/drifted schema | readiness false；不auto migrate/repair |
| ES08-A043 | registry/Workflow/handler/space digest drift | readiness false且safe finding exact |
| ES08-A044 | live object/vector/pointer inconsistency | readiness false/P0；不跳过bad row |
| ES08-A045 | `/livez` under provider outage/DB drift | 200 only loop alive；不冒充readiness |
| ES08-A046 | `/readyz` safe disclosure | exact200/503；body不含schema/path/provider/resource detail |
| ES08-A047 | business request while not-ready | auth后503，zero new business effect |
| ES08-A048 | SIGTERM during request/UoW/provider/child | 45s内bounded drain；truth按各窗口收敛 |
| ES08-A049 | SIGKILL at every startup/runtime window | WAL/fence/outbox/reservation recovery；无假terminal |
| ES08-A050 | prior serve operational run missing outcome | exclusive next boot写indeterminate；不猜clean shutdown |

### 8.6 Observability 与 operational ledger

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A051 | telemetry schema/golden | canonical bounded JSON；trace/correlation/causation贯穿 |
| ES08-A052 | malicious body/header/URL/provider error logging | value被禁止/脱敏；no fallback raw exception |
| ES08-A053 | metric label cardinality scan | onlyclosed labels；no UUID/URL/query/digest/message |
| ES08-A054 | `/internal/metrics` invalid/valid token | invalid401 pre-detail；valid bounded catalog only |
| ES08-A055 | log/metric/trace outage | business truth/effect不改变；failure仍有typed owner evidence |
| ES08-A056 | operational run same key/same digest replay | original run/outcome；no duplicate effect |
| ES08-A057 | operational run same key/different digest | conflict；history不改 |
| ES08-A058 | step ordinal/duplicate/after-terminal append | DB constraint/guard拒绝 |
| ES08-A059 | succeeded outcome missing/failed required step | completion拒绝；不能greenwash |
| ES08-A060 | crash betweenowner effect/step/outcome | owner readback+idempotency收敛；one effect/terminal outcome |

### 8.7 Backup、restore、retention 与 recovery

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A061 | backup while serve owns lock | fail；无partial complete manifest |
| ES08-A062 | quiesced backup crash at every step | onlyverified final或isolated tmp；active data不受损 |
| ES08-A063 | backup DB/object/vector/reference closure | everydigest/FK/count matches，包含live/grace data |
| ES08-A064 | backup retention 7/last2 rule | new verified before old delete；last2永不删 |
| ES08-A065 | restore nonempty/active target | rejected；no overwrite/merge |
| ES08-A066 | isolated restore drill | full schema/FK/object/vector/pointer/semantic validation通过 |
| ES08-A067 | process detail cleanup before/after | 90d+fence；Task/items/generation/lineage/result digest等价 |
| ES08-A068 | retrieval/delivery retention cutoff race | onlyeligible≥30d terminal rows；active/deadletter/inflight保留 |
| ES08-A069 | orphan/vector/invalid bytes cleanup with hold | rejected；grace/refs/current/serving/backup完整保护 |
| ES08-A070 | disk emergency cleanup pressure | 不缩短policy、不删protected truth/last backups；admission closes |

### 8.8 Cross-spec state、owner、atomicity 与 recovery

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A071 | StateFamily enum/schema scan | 仍恰六族；health/operation/secret/incident无status family |
| ES08-A072 | owner-write architecture scan | 每个state/pointer/proof只经来源ES owner port/UoW |
| ES08-A073 | log/queue/file/HTTP success substitution scan | zero business guard以这些事实判success |
| ES08-A074 | all named UoW fault injection | all-or-none、CAS0不成功、unknown commit先readback |
| ES08-A075 | outbox lost/duplicate/deadletter | truth不丢不重；closed repair不直改aggregate |
| ES08-A076 | retry/cancel/publication race | first valid owner CAS；no double terminal/serving |
| ES08-A077 | logical delete vs retrieval residual vector | dual fence zero leakage；cleanup later收敛 |
| ES08-A078 | provider/OCR/browser indeterminate | reserve/outcome事实完整；no same-call hidden retry |
| ES08-A079 | missing/corrupt object/vector recovery | exact restore/rebuild proof；no synthetic bytes/truth |
| ES08-A080 | manual SQL/path/object/vector/admin endpoint scan | no reachable surface；CLI onlyclosed typed commands |

### 8.9 Resource 与 measured safe envelope

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A081 | reference hardware manifest | CPU/RAM/disk/kernel/image exact且可复现 |
| ES08-A082 | HTTP 32+64 saturation | bounded memory/queue；excess503；accepted correctness100% |
| ES08-A083 | persistence queue256/UoW load | no unbounded growth、busy假success或cross-thread connection |
| ES08-A084 | Process8/Gemini4-2-1/OCR2/browser1 | semaphore ceilings从未超过；no starvation beyond owner policy |
| ES08-A085 | max request/raw/decompress/scatter transaction | limits内correct；+1 fail-loud、no partial acceptance |
| ES08-A086 | vector 50k Team/200k process exact scan | configured concurrency/deadline内correct或effective ceiling降低 |
| ES08-A087 | retrieval top20/320 recall/context32k | memory/time/traceback全通过；no raw vector |
| ES08-A088 | 30-minute steady+fault load | no OOM/integrity/state/proof failure；RSS/CPU/disk/queue留20%headroom |
| ES08-A089 | measured lower than provisional | effective config自动采用lower tested ceiling；release manifest记录 |
| ES08-A090 | attempted ceiling increase without evidence | startup/release拒绝；不触发ANN/shard/new service |

### 8.10 End-to-end、semantic、scope 与 release closure

| ID | Scenario | HARD assertion |
|---|---|---|
| ES08-A091 | four source kinds representative E2E | intake→clean→LS-RAG→vector→publication→retrieval完整proof |
| ES08-A092 | single/scatter/metadata/rebuild/deactivate/delete E2E | exactTask/asset/pointer/cleanup语义，no hidden branch |
| ES08-A093 | failure/cancel/retry/Gate/recovery E2E | caller可poll解释；无permanent stranded/false success |
| ES08-A094 | retrieval positive/negative/error E2E | grounded hits/traceback、honest empty、dependency5xx exact |
| ES08-A095 | ES-07 16-document/32-query semantic gate | recall/grounded/MRR/traceback/leakage thresholds全部通过 |
| ES08-A096 | acceptance manifest enumeration | ES01 45+ES02 60+ES03 86+ES04 112+ES05 110+ES06 94+ES07 115+ES08 100=722，无缺号/duplicate |
| ES08-A097 | Owner Truth trace matrix | OT01..04每条constraint至少一个HARD evidence；无execution反向改Truth |
| ES08-A098 | file/domain/capacity inventory | 恰4 OT+8 ES、6 StateFamily、8 Workflow、26 Process manifests、126 physical tables |
| ES08-A099 | legacy/import/runtime dependency scan | code/image/config/DDL/API/event/startup/fixtures零legacy/Cloudflare/D1/R2/SMCP依赖 |
| ES08-A100 | release promotion negative/positive | 任一HARD失败阻止；全部通过产生one signed evidence manifest，无waiver |

### 8.11 必须交付的 evidence bundle

1. OCI digest/signature、SBOM、provenance、source/dependency/system package locks；
2. container user/capability/seccomp/mount/network/PID/resource inspection；
3. RuntimeConfig/SecretManifest schemas、golden/negative/drift/rotation reports；
4. TLS/auth/Team/HTTP framing/body/rate/concurrency/disclosure security report；
5. SSRF DNS/IP/redirect/registered API/Gemini/browser/archive adversarial corpus；
6. startup/readiness/liveness/shutdown/SIGKILL/operation factual traces；
7. closed log/trace/metric catalogs与secret/content/cardinality scan；
8. 三张operational logical→physical DDL mapping、constraints、UoW fault matrix；
9. backup/restore/retention/cleanup/recovery drills与before/after truth digests；
10. reference hardware、workload、30-minute soak、fault、effective envelope report；
11. ES-01..08 722项acceptance manifest与Owner/baseline/legacy trace matrix；
12. 16-document/32-query semantic metrics及four-source/full-lifecycle end-to-end proof；
13. exact StateFamily/Workflow/Process/table/file/capability inventory diff；
14. zero-legacy dependency and no-scope-expansion signed report。

### 8.12 Final cross-spec truth audit

本节是ES-08-v1.0的规范级审计闭包，并为`ES08-A096..A100`定义exact trace输入。区间写法均为inclusive，表示区间内每一个ID，不允许抽样、跳号或以cluster名称替代单条release evidence。权威顺序固定为Owner Truth → baseline locked Truth → Execution Spec → legacy evidence。

#### 8.12.1 Owner Truth全量映射

| Frozen cluster | Normative execution authority | HARD closure set |
|---|---|---|
| `OT01-T001..T015` | ES-01 §1/§4..6；ES-02/03/05/06/07 §1..7；ES-08 §1..7 | `ES01-A001..A045`、`ES03-A001..A086`、`ES05-A001..A110`、`ES06-A001..A094`、`ES07-A001..A115`、`ES08-A091..A100` |
| `OT01-N001..N009` | ES-01..08 §2、§3、§7及rejected alternatives | `ES01-A031..A045`、`ES05-A101..A110`、`ES07-A107..A115`、`ES08-A080/A098..A100` |
| `OT01-C001..C010` | ES-01..08 ownership、port、protocol、scope与release contracts | `ES01-A001..A045`、`ES02-A001..A060`、`ES08-A071..A100` |
| `OT02-T001..T023` | ES-01 Task；ES-02 Execution/Process；ES-03 Intake/Gate；ES-05/06/07 derived facts；ES-04/08 owner guard | `ES01-A005..A030`、`ES02-A013..A060`、`ES03-A035..A086`、`ES08-A071..A080/A097..A100` |
| `OT02-N001..N010` | ES-01..08 state-vs-fact、identity、pointer、projection与cleanup non-scope | `ES01-A029..A032`、`ES02-A013/A027/A055..A060`、`ES03-A077..A086`、`ES08-A071..A080/A098..A100` |
| `OT02-C001..C010` | ES-01/02/03 unique transition owners；ES-04 named UoW；ES-06/07 derived lineage；ES-08 recovery | `ES02-A013..A060`、`ES03-A077..A086`、`ES04-A001..A112`、`ES08-A071..A080/A096..A100` |
| `OT03-T001..T032` | ES-01 external contract；ES-02 Workflow；ES-03 source/clean/Gate；ES-05 inference；ES-06 LS-RAG；ES-07 retrieval；ES-08 transport/security | `ES01-A001..A045`、`ES02-A001..A060`、`ES03-A001..A086`、`ES05-A001..A110`、`ES06-A001..A094`、`ES07-A001..A115`、`ES08-A091..A100` |
| `OT03-N001..N015` | ES-01/07 no raw-vector/final-answer contract；ES-02/05 finite registry；ES-08 no platform/operator surface | `ES01-A031/A032/A037..A045`、`ES05-A101..A110`、`ES07-A107..A115`、`ES08-A080/A098..A100` |
| `OT03-C001..C016` | ES-01..08 exact contract、source、Task、schema、kernel、retrieval与no-raw-vector boundaries | `ES01-A001..A045`、`ES03-A001..A086`、`ES06-A001..A094`、`ES07-A001..A115`、`ES08-A091..A100` |
| `OT04-T001..T035` | ES-01..07完整journey/failure evidence；ES-07 §8 semantic gate；ES-08 §4.10/§8/§9 release gate | 全项目`ES01-A001..ES08-A100` manifest；重点`ES07-A096..A115`、`ES08-A081..A100` |
| `OT04-N001..N017` | ES-01..08 §2/§3/§7/§9 rejected alternatives与fixed-capacity audit | `ES01-A031..A045`、`ES04-A097..A112`、`ES07-A107..A115`、`ES08-A080/A090/A098..A100` |
| `OT04-C001..C015` | ES-01..08 acceptance bundles、negative paths、fault/recovery、semantic与scope gates | `ES01-A001..A045` + `ES02-A001..A060` + `ES03-A001..A086` + `ES04-A001..A112` + `ES05-A001..A110` + `ES06-A001..A094` + `ES07-A001..A115` + `ES08-A001..A100` |

上述12个inclusive cluster覆盖4份Owner Truth本体的207个唯一ID：OT-01 34、OT-02 43、OT-03 63、OT-04 67。Owner文件中对上游OT ID的引用不重复计数。

#### 8.12.2 Baseline locked Truth闭包

| Locked source | Final authority | Audit result |
|---|---|---|
| baseline index `OD-01..12` | OT-01/03；ES-01/04/05/08 | standalone、单体、Team/token、Turso、adapter-first、LS-RAG、无UI/平台全部保留 |
| `S01-v1.5` | OT-01/03；ES-01/08 | caller-neutral contract、最小Team、Task/Audit/poll与internal token闭合 |
| `D01-v1.4` | OT-02；ES-01/02 | Task→Execution→Process、single/scatter、control/proof方向闭合 |
| `S02-v1.3 / T-O-1..11` | OT-03；ES-01/02 | Task六态、CAS、collect-all、cancel、retry/rebuild、readiness、lineage闭合 |
| `S03-v1.3 / T-O-12..29` | ES-02/04/08 | 8 Workflow、Execution/Process八态、claim/fence/retry/recovery、typed outcome闭合 |
| `S04-v1.2 / T-O-30..48` | OT-02；ES-03/04/07 | 五类Intake identity、immutable Revision、acceptance、serving/lifecycle/cleanup闭合 |
| `S05-v1.1 / T-O-49..76` | OT-03；ES-03/05/08 | 四类source、clean、typed evidence、mandatory preflight与Gate闭合 |
| `S06 T-O-77..85` | OT-03；ES-05/06/07 | immutable generation/current、versioned structure、kernel/extension/repair与retrieval handoff闭合 |
| `D02-v1.0 / T-O-86..92` | OT-02；ES-01..08 | 六StateFamily、唯一owner、state-vs-fact、非法边与drift fail-closed闭合 |
| glossary v1.4 | OT-01..04；ES-01..08 | canonical identity、ledger、pointer、proof与derived asset spelling无冲突 |

Baseline中未冻结候选、旧16域编排、Cloudflare/D1/R2/SMCP/legacy wire/schema/status均未获得Truth地位。`legacy-family/`和`legacy-python/`只保留reference anchor，runtime/build/config/DDL/API/event/fixture零依赖。

#### 8.12.3 Set-exact inventory与冲突结论

| Dimension | Frozen result | Conflict / blind-spot result |
|---|---|---|
| Files | 4份Owner Truth frozen + 8份Execution Spec ready | 无第13份spec、影子索引或执行owner-gate |
| Owner IDs | 207 unique、连续、无缺号 | 无未映射foundational Truth；0 open Owner QNA |
| StateFamily | Task 6、Execution 8、Process 8、IntakeItem 3、CandidateSet 4、ExecutionGate 4 | exact set与D02/OT-02一致；无第七族、双owner或组合状态 |
| Public contract | 32条table-declared `/v1` routes + 1条同步retrieval route = 33；6个异步intent；3条非产品operational GET | 无raw vector、final answer、callback、admin/operator、generic object/vector surface |
| Catalogs | 4 source kinds、8 Workflow、26 Process manifests | ES-02/03/05/06/07集合相等；无legacy alias或dynamic plugin |
| Interfaces/protocols | 所有cross-spec `*Port`引用均解析到既有owner declaration；consumer stub只作依赖标注 | 无未声明port、同名语义分叉或旧泛称/错名残留；durable schema/event spelling一致 |
| Persistence | 113 owner tables + 13 infrastructure tables = 126 physical tables | ES-04 mapping无missing/extra/duplicate；engine catalog不计入 |
| Atomicity | 55个named UoW | key唯一；跨owner effect均有固定owner port、CAS/fence与fault assertion |
| Acceptance | 45+60+86+112+110+94+115+100 = 722 HARD definition IDs | 各文件definition row从001连续到末号，无duplicate、skip或waiver；trace引用不重复计数 |
| Semantic gate | 16-document / 32-query bounded corpus | 只验证grounded retrieval usefulness；不扩为SLA、平台或final-answer评测 |
| Retention/recovery | canonical skeleton、owner proof/pointer与operational facts保持；detail/payload/evidence按§4.12有限清理 | 各清理UoW有age/ref/hold/serving/backup fence；无互相冲突的duration或假恢复 |
| Deployment/security | one image/container/long-lived Python process、one embedded DB、one local CAS root、finite CLI | 无第二服务/backend、RBAC、operator platform、HA或远程控制面 |
| Legacy/scope | zero runtime dependency；固定4+8文件与既有产品边界 | 无scope expansion；所有新增内容均为既有能力的有限executional实现 |

审计结果：在规范层没有发现Truth冲突、未归属状态写入、schema孤儿、协议断点、未闭合executional槽位或产品面泄漏。所有实施期不确定性都已被收口为exact default + HARD验证/变更证据，不能回流为Owner问题。`ready/specification-ready`只声明规范闭合；它不声称尚未构建的实现、硬件测量或722项release evidence已经实际通过。

---

## 9. Remaining Technical Decisions and Defaults

本节没有Owner问题。所有值都是single-process safety guard或release test profile，不是吞吐、可用性、延迟、RPO/RTO或容量的Owner承诺。

### 9.1 已裁决 runtime defaults

| Topic | V1 exact default | Change evidence |
|---|---|---|
| Release | one OCI image by digest、one container、one long-lived Python process | foundational topology reopen才可增加unit |
| Python/server | CPython 3.12 exact patched build；FastAPI/Pydantic v2；Uvicorn1 worker/no reload | dependency/security/full acceptance |
| Ingress | HTTPS `0.0.0.0:8443` inside container；host private CIDR only | network/TLS evidence；no plaintext/public bind |
| TLS | min1.2、prefer1.3、restart rotation | compatibility+security evidence |
| Token | 32 random bytes base64url；current1+previous≤1/24h | simple-token Truth不可改变 |
| HTTP | header16KiB、body8MiB、active32、wait64、keepalive5s | measured envelope可下调 |
| Rate | token50/s burst100；Team read20/40、mutation5/10、retrieval2/4 | abuse/load evidence可下调；非quota |
| Runtime | Process8、persistence queue256、outbox batch64 | real driver/load evidence |
| Scanners | outbox1s、runtime lease/stranded5s、candidate/retention/cleanup60s、full integrity24h | fault/load evidence可上调但不得超过最短lease/recovery安全窗口 |
| Adapters | Gemini4/team2/process1；OCR2；browser1；object streams4 | upstream max + measured envelope |
| Health | cheap check5s、loop tick5s、full scan24h | fault/recovery cost evidence |
| Shutdown | request10s、total30s、child TERM→KILL5s、container45s | ambiguity/recovery evidence |
| Disk | warn80%、not-ready90% or <2GiB、emergency95% | target volume/fault evidence；only tighten |
| Backup | every≤24h、critical72h、latest7/min2、restore drill each release/90d | verified operational evidence |
| Retention | §4.12 exact values；batch500 rows/64MiB | lineage/capacity evidence；cannot weaken guards |
| Logs | JSON stdout/stderr、INFO、14d/2GiB | privacy/diagnostic evidence |
| Metrics | closed catalog、scrape valid token、10s update | bounded-cardinality evidence |

### 9.2 Measured safe operating envelope protocol

Initial reference profile `mkb-r1`：Linux x86_64、4 dedicated vCPU、16 GiB RAM、100 GiB local SSD data volume、独立100 GiB backup volume、1 GiB `/dev/shm`、2 GiB temp；exact kernel/filesystem/drive/image digests写release evidence。该profile只是首个可复现实测起点。

Measurement固定步骤：

1. fresh DB与restore DB各跑一次；
2. 加载边界语料：8MiB request、64MiB raw、256MiB decompressed、10,000 candidate/member transaction、50,000 active vectors/Team与200,000/process candidate ceiling；
3. 15分钟warm-up + 30分钟steady mixed read/mutation/retrieval + fault sweep；
4. 同时覆盖HTTP32、Process8、Gemini4、OCR2、browser1、retrieval4、persistence queue pressure；
5. 记录correctness、deadline、RSS/CPU/disk/fsync/queue、child/PID、recovery、semantic metrics；
6. 要求zero OOM、zero integrity/state/proof/leakage failure，且RSS/CPU/disk/queue持续峰值≤80% hard allocation；
7. 每一guard的effective ceiling取“不超过upstream provisional、通过全部test且保留≥20%headroom”的最大已测值；
8. 任一候选上限未通过就降低config并重跑，不能以增加service/DB/ANN/shard解决；
9. 提高effective ceiling必须new release、same protocol与signed evidence；
10. 如果最小单请求/单Process/单retrieval都不能通过，release失败而不是继续降低语义质量。

文档不能在无实现/硬件的情况下伪称“已测”。ES-08-v1.0冻结measurement contract与provisional ceilings；每个可部署build的`ReleaseEvidenceManifestV1`才是该build的actual measured envelope authority。

### 9.3 Release gate 与无 waiver 规则

Promotion顺序：

~~~text
build reproducibility + signature/SBOM
  → fresh/upgrade schema+registry bootstrap
  → unit/property/contract/architecture tests
  → real Turso transaction/object/vector tests
  → security/SSRF/path/secret/disclosure tests
  → crash/fault/recovery/backup/restore tests
  → resource/soak measured envelope
  → four-source full lifecycle E2E
  → 16/32 semantic gate
  → 722-ID trace/inventory/legacy/scope audit
  → signed ReleaseEvidenceManifestV1
~~~

`HARD`没有waiver、skip、allow-failure、manual green或threshold lowering。外部provider暂时不可用导致live canary无法运行时，release保持blocked；不换provider或把canary改为mock。Only `not_applicable` for a step whose closed catalog explicitly proves the release lacks that path,但V1已冻结四source/Browser/OCR/Gemini/vector，因此这些核心path都required。

### 9.4 Rejected alternatives

| Alternative | Rejection |
|---|---|
| Kubernetes/operator/microservices | 超过一个deployment unit并复制状态/网络/运维面 |
| multiple Uvicorn workers | embedded DB ownership、in-memory limiter与runner会分叉 |
| Gunicorn/remote queue/sidecar scheduler | 增加process/service与delivery topology |
| public HTTP behind “trusted network” only | simple token不等于无TLS/网络边界 |
| environment secret/config values | 易泄漏、隐式优先级/hot drift、不可审计 |
| hot config/secret/model reload | running binding无法复现，rotation/rollback歧义 |
| team-scoped token/RBAC/operator role | foundational trust model明确不支持 |
| generic admin/repair/SQL/object/vector endpoint | 新产品/攻击面，可绕owner guard |
| unrestricted URL/browser/proxy | SSRF、credential exfiltration与resource abuse |
| root Chromium或`--no-sandbox` | untrusted web content突破单体边界风险不可接受 |
| provider fallback/model alias | exact binding/Invocation/semantic evidence失真 |
| log/metric-only failure | crash/retention后不可审计，违反typed evidence |
| online backup/migration/HA | Owner无该SLA且会增加分布式状态/服务 |
| cleanup on disk pressure without proof | 会删除canonical/current/serving truth并假恢复 |
| benchmark as Owner SLA | measurement只定义build安全guard，不扩大产品承诺 |
| release waiver | 使冻结Truth和semantic gate失去约束力 |

### 9.5 Closure

ES-08没有需要Owner回答的问题。Token carrier/rotation、TLS、container、config、secret、egress、health、metric、retention、backup cadence、resource ceiling、benchmark与runbook全部是已冻结产品边界内的executional选择；最终truth/contract/schema/state/UoW/acceptance审计已在§8.12闭合。任何未来提议若增加deployment unit、auth角色、operator API、remote backend、HA、raw diagnostic/vector surface或产品SLA，必须先按index scope audit处理；不能在本文件中“预留”。

---

## 10. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| ES-08-v0.1 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 继承4份frozen Owner Truth、D01/D02、S01..05与ES-01..07，冻结一个OCI/一个长期Python process的单体部署、strict config/secret、simple-token rotation、TLS/ingress、SSRF/egress/browser sandbox、bounded runtime、health/readiness/shutdown、closed telemetry/metrics、local finite CLI、3张operational evidence tables、backup/restore/retention/recovery、measured envelope contract与100项HARD release acceptance。未新增产品能力、StateFamily、Workflow、Process capability、provider、backend、service、deployment unit、operator platform或spec文件。 |
| ES-08-v1.0 | 2026-08-10 | ready | 完成4份Owner Truth 207 ID、全部baseline locked Truth与ES-01..08最终trace audit；set-exact冻结6 StateFamily、33产品routes、4 source、8 Workflow、26 Process、113 owner + 13 infrastructure tables、55 UoW及722项HARD acceptance。审计未发现Truth冲突、schema/协议盲点或scope leak；不声称实现期release evidence已执行。未新增产品能力、状态族、服务、backend、deployment unit、operator平台或spec文件。 |
