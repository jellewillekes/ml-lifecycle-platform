# Changelog

All important changes and updates to this project are documented here.

This repo uses Conventional Commits and Release Please.

## [0.5.6](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.5.5...v0.5.6) (2026-07-23)


### Features

* add batch drift MVP against windowed events ([#250](https://github.com/jellewillekes/ml-lifecycle-platform/issues/250)) ([353a10a](https://github.com/jellewillekes/ml-lifecycle-platform/commit/353a10ab3a6217dcf5566b42c808f914fadf7530)), closes [#209](https://github.com/jellewillekes/ml-lifecycle-platform/issues/209)
* add event-plane prediction and label contracts ([#242](https://github.com/jellewillekes/ml-lifecycle-platform/issues/242)) ([64f69f4](https://github.com/jellewillekes/ml-lifecycle-platform/commit/64f69f4258f311c5d4158c858a86a96573c01e93)), closes [#198](https://github.com/jellewillekes/ml-lifecycle-platform/issues/198) [#205](https://github.com/jellewillekes/ml-lifecycle-platform/issues/205)
* add multi-model spec-driven orchestration ([#244](https://github.com/jellewillekes/ml-lifecycle-platform/issues/244)) ([8a2bfcd](https://github.com/jellewillekes/ml-lifecycle-platform/commit/8a2bfcddc29fbc04335ca0818ca02c1d54a821a1)), closes [#202](https://github.com/jellewillekes/ml-lifecycle-platform/issues/202)
* add one-command GCP teardown and restore runbook ([#252](https://github.com/jellewillekes/ml-lifecycle-platform/issues/252)) ([e71bda2](https://github.com/jellewillekes/ml-lifecycle-platform/commit/e71bda2c78dad143e091ec68e1f4dbb06ea65420)), closes [#251](https://github.com/jellewillekes/ml-lifecycle-platform/issues/251)
* add prediction event sink with JSONL and BigQuery adapters ([#245](https://github.com/jellewillekes/ml-lifecycle-platform/issues/245)) ([b816c3d](https://github.com/jellewillekes/ml-lifecycle-platform/commit/b816c3d6bcdb8ab194b8777d8adae97fd5429b6d)), closes [#203](https://github.com/jellewillekes/ml-lifecycle-platform/issues/203)
* add release-linked drift baselines ([#247](https://github.com/jellewillekes/ml-lifecycle-platform/issues/247)) ([d6a2ac2](https://github.com/jellewillekes/ml-lifecycle-platform/commit/d6a2ac2673d68655fd9f5a513c091d2bca00a671)), closes [#206](https://github.com/jellewillekes/ml-lifecycle-platform/issues/206)


### Bug Fixes

* grant CI service account BigQuery admin for event plane ([#246](https://github.com/jellewillekes/ml-lifecycle-platform/issues/246)) ([13cc1bd](https://github.com/jellewillekes/ml-lifecycle-platform/commit/13cc1bd1720543bfe4ed8efe1e59a57f28c2abbe)), closes [#203](https://github.com/jellewillekes/ml-lifecycle-platform/issues/203)

## [0.5.5](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.5.4...v0.5.5) (2026-06-19)


### Features

* add DataSource port and first Binance OHLCV model ([#234](https://github.com/jellewillekes/ml-lifecycle-platform/issues/234)) ([bcac842](https://github.com/jellewillekes/ml-lifecycle-platform/commit/bcac842b901e37c4665b6e697c211df4dc90887f))
* add hosted staging Binance pipeline job ([#235](https://github.com/jellewillekes/ml-lifecycle-platform/issues/235)) ([e8cdcf2](https://github.com/jellewillekes/ml-lifecycle-platform/commit/e8cdcf2e3362a110774242255af04f29287c3915)), closes [#201](https://github.com/jellewillekes/ml-lifecycle-platform/issues/201)
* add LightGBM trainer and use it for binance model ([#238](https://github.com/jellewillekes/ml-lifecycle-platform/issues/238)) ([780902d](https://github.com/jellewillekes/ml-lifecycle-platform/commit/780902dc7a669f24e3181e8affb7a942b6fe7400)), closes [#237](https://github.com/jellewillekes/ml-lifecycle-platform/issues/237)
* add production environment infrastructure ([#227](https://github.com/jellewillekes/ml-lifecycle-platform/issues/227)) ([a161833](https://github.com/jellewillekes/ml-lifecycle-platform/commit/a16183315d22f9783ccc7d78ddeceffd155d8d21)), closes [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175)
* add validate_data pipeline stage ([#239](https://github.com/jellewillekes/ml-lifecycle-platform/issues/239)) ([c9ff8d8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/c9ff8d84b6771a58fa9edc9ae17f09f01f552b1c)), closes [#199](https://github.com/jellewillekes/ml-lifecycle-platform/issues/199)
* add validate_model pipeline stage ([#240](https://github.com/jellewillekes/ml-lifecycle-platform/issues/240)) ([13dc348](https://github.com/jellewillekes/ml-lifecycle-platform/commit/13dc348779f4ccb44adc477206e6ba5e66a4f223)), closes [#200](https://github.com/jellewillekes/ml-lifecycle-platform/issues/200)
* split CI SA, scope WIF to staging environment, add prod skeletons ([#226](https://github.com/jellewillekes/ml-lifecycle-platform/issues/226)) ([cf62ff2](https://github.com/jellewillekes/ml-lifecycle-platform/commit/cf62ff268d1a82e087a91fb4b6d734a6c40bf3f3))
* updated roadmap ([#197](https://github.com/jellewillekes/ml-lifecycle-platform/issues/197)) ([5925049](https://github.com/jellewillekes/ml-lifecycle-platform/commit/592504963bc00e0a96452eee2c53753aa9fdb706))


### Bug Fixes

* gate production foundation behind manage_production_foundation ([#230](https://github.com/jellewillekes/ml-lifecycle-platform/issues/230)) ([1d153f0](https://github.com/jellewillekes/ml-lifecycle-platform/commit/1d153f028efa2e0dacfb6b4f2da939ffe1eee435)), closes [#175](https://github.com/jellewillekes/ml-lifecycle-platform/issues/175)


### Dependencies

* **actions:** bump github/codeql-action in the github-actions group ([#195](https://github.com/jellewillekes/ml-lifecycle-platform/issues/195)) ([af2ffc8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/af2ffc8576ff3a1dcedccb6a148c0f2137662f67))
* **actions:** bump the github-actions group across 1 directory with 7 updates ([#186](https://github.com/jellewillekes/ml-lifecycle-platform/issues/186)) ([ab61142](https://github.com/jellewillekes/ml-lifecycle-platform/commit/ab61142e91ac9a0b5d688f8ebb5de9f8d1cd2600))


### Documentation

* consolidate architecture docs and move diagrams ([#224](https://github.com/jellewillekes/ml-lifecycle-platform/issues/224)) ([637fd63](https://github.com/jellewillekes/ml-lifecycle-platform/commit/637fd6339afa8f2016a5a5a5c1c32d6482b7d790)), closes [#168](https://github.com/jellewillekes/ml-lifecycle-platform/issues/168)

## [0.5.4](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.5.3...v0.5.4) (2026-04-20)


### Features

* add observability alerts and serving SLOs ([#190](https://github.com/jellewillekes/ml-lifecycle-platform/issues/190)) ([57c0d42](https://github.com/jellewillekes/ml-lifecycle-platform/commit/57c0d42315380d8a0e5526512eb762f3ad563fec)), closes [#174](https://github.com/jellewillekes/ml-lifecycle-platform/issues/174)
* add observability dashboards for serving, jobs, and releases ([#184](https://github.com/jellewillekes/ml-lifecycle-platform/issues/184)) ([ff3dbc7](https://github.com/jellewillekes/ml-lifecycle-platform/commit/ff3dbc7b0fcb891828d45cfacde2559572b42c3a)), closes [#173](https://github.com/jellewillekes/ml-lifecycle-platform/issues/173)
* gcp-native alert routing for grafana managed alerts ([#191](https://github.com/jellewillekes/ml-lifecycle-platform/issues/191)) ([eb701f4](https://github.com/jellewillekes/ml-lifecycle-platform/commit/eb701f46e36001a1cacdd9c3c5d180d06e6574a6))
* self-hosted observability stack on GCE VM ([#179](https://github.com/jellewillekes/ml-lifecycle-platform/issues/179)) ([e674fcc](https://github.com/jellewillekes/ml-lifecycle-platform/commit/e674fccd65c5401a6c0dcd91ec67784dec31b25f)), closes [#172](https://github.com/jellewillekes/ml-lifecycle-platform/issues/172)
* self-hosted observability stack on GCE VM ([#181](https://github.com/jellewillekes/ml-lifecycle-platform/issues/181)) ([ea0c9d3](https://github.com/jellewillekes/ml-lifecycle-platform/commit/ea0c9d3fae8b834fb307ffc177a6c9aee4342ceb)), closes [#172](https://github.com/jellewillekes/ml-lifecycle-platform/issues/172)
* upload grafana dashboard json to observability config bucket ([#187](https://github.com/jellewillekes/ml-lifecycle-platform/issues/187)) ([476e042](https://github.com/jellewillekes/ml-lifecycle-platform/commit/476e042bfa45ca08eef81875cd45c6203a091f08)), closes [#185](https://github.com/jellewillekes/ml-lifecycle-platform/issues/185)
* upload grafana dashboard json to observability config bucket ([#188](https://github.com/jellewillekes/ml-lifecycle-platform/issues/188)) ([e680a4a](https://github.com/jellewillekes/ml-lifecycle-platform/commit/e680a4a4364638fa8d722647f1f02445c738adc9)), closes [#185](https://github.com/jellewillekes/ml-lifecycle-platform/issues/185)


### Bug Fixes

* **observability:** disable deletion_protection on alert-router ([#192](https://github.com/jellewillekes/ml-lifecycle-platform/issues/192)) ([9ad27e5](https://github.com/jellewillekes/ml-lifecycle-platform/commit/9ad27e53efb4c3b23d8063c6fd350f61157744fe))


### Documentation

* add platform roadmap ([#193](https://github.com/jellewillekes/ml-lifecycle-platform/issues/193)) ([453db10](https://github.com/jellewillekes/ml-lifecycle-platform/commit/453db109a78017f19b4e0dc67d9d468e88388ce9))

## [0.5.3](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.5.2...v0.5.3) (2026-04-18)


### Features

* add cloud scheduler support for cr jobs ([#119](https://github.com/jellewillekes/ml-lifecycle-platform/issues/119)) ([7904c01](https://github.com/jellewillekes/ml-lifecycle-platform/commit/7904c0182f87548aa804bdee633c0b6e575a6b8a))
* add hosted serving staging baseline workflow ([#109](https://github.com/jellewillekes/ml-lifecycle-platform/issues/109)) ([9e241cd](https://github.com/jellewillekes/ml-lifecycle-platform/commit/9e241cd83b9aebf088a62b990c8fe10ba461ace5))
* add OpenTelemetry runtime instrumentation for serving and jobs ([#176](https://github.com/jellewillekes/ml-lifecycle-platform/issues/176)) ([d2da11f](https://github.com/jellewillekes/ml-lifecycle-platform/commit/d2da11f042c52e1f072ad67b3707d1a11eb89a9f)), closes [#171](https://github.com/jellewillekes/ml-lifecycle-platform/issues/171)
* ci add docs and infra validation ([#138](https://github.com/jellewillekes/ml-lifecycle-platform/issues/138)) ([fd8c6cc](https://github.com/jellewillekes/ml-lifecycle-platform/commit/fd8c6cc8b54547c7ab117aeb62b5579622bff380))
* ci cd trigger policy ([#137](https://github.com/jellewillekes/ml-lifecycle-platform/issues/137)) ([ba77fcd](https://github.com/jellewillekes/ml-lifecycle-platform/commit/ba77fcd607bc5de590f31f92a4790591f082e315))
* deploy platform workflows as cloud run jobs ([#114](https://github.com/jellewillekes/ml-lifecycle-platform/issues/114)) ([8ec3f03](https://github.com/jellewillekes/ml-lifecycle-platform/commit/8ec3f03f251cb67b3e8ca87903e78a3122e5cff0))
* make hosted staging golden path deterministic ([#131](https://github.com/jellewillekes/ml-lifecycle-platform/issues/131)) ([28c4a25](https://github.com/jellewillekes/ml-lifecycle-platform/commit/28c4a255313579aa92f07e3983b65eead825f12e))


### Bug Fixes

* fix local operator path and golden-path validation ([#129](https://github.com/jellewillekes/ml-lifecycle-platform/issues/129)) ([a2a41d1](https://github.com/jellewillekes/ml-lifecycle-platform/commit/a2a41d1f7e1355fe23e1b9996fa91708c15fb13a))
* hotfix cloud golden path ([#133](https://github.com/jellewillekes/ml-lifecycle-platform/issues/133)) ([4fffd57](https://github.com/jellewillekes/ml-lifecycle-platform/commit/4fffd57a02f763cd814cef07e5b125ea0c08445a))
* hotfix cr jobs ([#118](https://github.com/jellewillekes/ml-lifecycle-platform/issues/118)) ([8ccd49e](https://github.com/jellewillekes/ml-lifecycle-platform/commit/8ccd49ea937a00221e8305372ab6c59dcf3b84e8))
* read compose AWS creds from MLP_COMPOSE_* env vars ([#150](https://github.com/jellewillekes/ml-lifecycle-platform/issues/150)) ([f6327f4](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f6327f41d9cf4f7c19ec0bc8aa171bb8263d789d)), closes [#142](https://github.com/jellewillekes/ml-lifecycle-platform/issues/142)
* retry MLflow staging health probe and drop Cloud Run cold-start flakes ([#147](https://github.com/jellewillekes/ml-lifecycle-platform/issues/147)) ([6959995](https://github.com/jellewillekes/ml-lifecycle-platform/commit/6959995abd2c8b4c5a42d42bb45b3dbf72caa37b)), closes [#146](https://github.com/jellewillekes/ml-lifecycle-platform/issues/146)
* shorten workflow names for README badges ([#140](https://github.com/jellewillekes/ml-lifecycle-platform/issues/140)) ([180d991](https://github.com/jellewillekes/ml-lifecycle-platform/commit/180d99156d81e7fbd6f99a3b5a504b705595989c))
* stabilize hosted mlflow and staging baseline workflows ([#112](https://github.com/jellewillekes/ml-lifecycle-platform/issues/112)) ([18deee4](https://github.com/jellewillekes/ml-lifecycle-platform/commit/18deee477b5a3f2eff594471db249cc7361affab))


### Documentation

* add current operator guide for local and hosted paths ([#120](https://github.com/jellewillekes/ml-lifecycle-platform/issues/120)) ([1cb497f](https://github.com/jellewillekes/ml-lifecycle-platform/commit/1cb497f7a31c4352afa52d17a87b1574be87b91b))
* add simplification charter (P01) ([#157](https://github.com/jellewillekes/ml-lifecycle-platform/issues/157)) ([77cc6b7](https://github.com/jellewillekes/ml-lifecycle-platform/commit/77cc6b7739672e04a07862847a10b8fa1d5d35a6))
* reset repo story and architecture truth for OSS contributors (P03) ([#158](https://github.com/jellewillekes/ml-lifecycle-platform/issues/158)) ([bda0b28](https://github.com/jellewillekes/ml-lifecycle-platform/commit/bda0b282135a0339dda6a4be7633ee5d764be3f6))
* verify post-cleanup state and bump Last verified dates ([#169](https://github.com/jellewillekes/ml-lifecycle-platform/issues/169)) ([b64f28c](https://github.com/jellewillekes/ml-lifecycle-platform/commit/b64f28cfa480ab88cd4c0403346f19756f7e76ba)), closes [#165](https://github.com/jellewillekes/ml-lifecycle-platform/issues/165)

## [0.5.2](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.5.1...v0.5.2) (2026-03-10)


### Features

* add GCP Terraform bootstrap root ([#89](https://github.com/jellewillekes/ml-lifecycle-platform/issues/89)) ([b31cfb1](https://github.com/jellewillekes/ml-lifecycle-platform/commit/b31cfb191cba755819a89d55c44e294ccd07e22f))
* emit release evidence bundles for promote rollback and reproduce ([#75](https://github.com/jellewillekes/ml-lifecycle-platform/issues/75)) ([df2301b](https://github.com/jellewillekes/ml-lifecycle-platform/commit/df2301bb1b06745299c46b9022d17abd8314af7d))
* harden hosted runtime and serving contracts ([#86](https://github.com/jellewillekes/ml-lifecycle-platform/issues/86)) ([ee55463](https://github.com/jellewillekes/ml-lifecycle-platform/commit/ee55463229a6ff8e138b66a0e02cb0fb544e13b7))
* improve hosted runtime and serving contracts ([#88](https://github.com/jellewillekes/ml-lifecycle-platform/issues/88)) ([8f68fcf](https://github.com/jellewillekes/ml-lifecycle-platform/commit/8f68fcf99ca5fd3969b1903acf04d889c2f7ed81))
* **serving:** enforce model-spec feature contracts ([#73](https://github.com/jellewillekes/ml-lifecycle-platform/issues/73)) ([c78e032](https://github.com/jellewillekes/ml-lifecycle-platform/commit/c78e032c640566187a5b7fa49e08e2152baea567))


### Documentation

* add platform handbook and local operator runbooks ([#76](https://github.com/jellewillekes/ml-lifecycle-platform/issues/76)) ([457a45c](https://github.com/jellewillekes/ml-lifecycle-platform/commit/457a45c6d52b9d747c9e03b12e59d8dc4b07bff7))
* m2 readiness alignment ([#103](https://github.com/jellewillekes/ml-lifecycle-platform/issues/103)) ([a2645f8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/a2645f85b5d19e66d9b62994a183484e8da3e45c))
* update readme ([#85](https://github.com/jellewillekes/ml-lifecycle-platform/issues/85)) ([482c074](https://github.com/jellewillekes/ml-lifecycle-platform/commit/482c0740d2a6edcd47c4fd25b2cfe03eab19915a))

## [0.5.1](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.5.0...v0.5.1) (2026-03-09)


### Features

* update model specs ([#70](https://github.com/jellewillekes/ml-lifecycle-platform/issues/70)) ([a6a8de8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/a6a8de852c8259d3fca25266d89e1b068ae91899))

## [0.5.0](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.4.0...v0.5.0) (2026-03-09)


### Features

* add dataset fingerprinting and lineage metadata ([#6](https://github.com/jellewillekes/ml-lifecycle-platform/issues/6)) ([1870812](https://github.com/jellewillekes/ml-lifecycle-platform/commit/1870812c01a6839b238173af37ac46d5994d32c5))
* add Prometheus metrics endpoint and structured logging ([#10](https://github.com/jellewillekes/ml-lifecycle-platform/issues/10)) ([71c61a8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/71c61a89c1722168cd3408f196365732f3368341))
* add promotion guardrails and rollback-prod ([#11](https://github.com/jellewillekes/ml-lifecycle-platform/issues/11)) ([ae80bb7](https://github.com/jellewillekes/ml-lifecycle-platform/commit/ae80bb7b6b4ca15393926c1ad24c87ba962bb11b))
* add release policy module and dry-run promotion gate ([#24](https://github.com/jellewillekes/ml-lifecycle-platform/issues/24)) ([23e4818](https://github.com/jellewillekes/ml-lifecycle-platform/commit/23e48188fa3309cf45c8249ec3ff264f00f8343e))
* alias-based release with prod/champion and updated docs ([5507a6d](https://github.com/jellewillekes/ml-lifecycle-platform/commit/5507a6dd74ebd0b895bf56453c6add047518c613))
* alias-based release with prod/champion and updated docs ([2bc92eb](https://github.com/jellewillekes/ml-lifecycle-platform/commit/2bc92eb2479e11a0b519e923badb3024854e25f6))
* **local-runtime-profile-cli:** implement local profile loader and CLI ([#64](https://github.com/jellewillekes/ml-lifecycle-platform/issues/64)) ([2f2c055](https://github.com/jellewillekes/ml-lifecycle-platform/commit/2f2c0553003da16d4fc9f713723f3d4c99aef2a5))
* reproduce registered models from source runs ([#35](https://github.com/jellewillekes/ml-lifecycle-platform/issues/35)) ([bc98ed8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/bc98ed8bba36d920aecacccd212193c1e9617019))
* **runtime:** add local backend adapter interfaces ([#62](https://github.com/jellewillekes/ml-lifecycle-platform/issues/62)) ([2f3bdc8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/2f3bdc8d364e5361cd13519934c73cbd27c98433))
* switch to alias-based MLflow releases (candidate/prod) ([b95318b](https://github.com/jellewillekes/ml-lifecycle-platform/commit/b95318b43aa171280cefbf0f7cf8d89b4047403e))
* switch to alias-based MLflow releases (candidate/prod) ([bb6b541](https://github.com/jellewillekes/ml-lifecycle-platform/commit/bb6b541e58859e41450b3bc22cf7218de761257c))


### Bug Fixes

* **ci:** allow deps type in PR title check ([#22](https://github.com/jellewillekes/ml-lifecycle-platform/issues/22)) ([1f310c1](https://github.com/jellewillekes/ml-lifecycle-platform/commit/1f310c19d88967e9194e68ebf5bc59ba9e51b962))
* **ci:** bootstrap Python and uv in E2E workflow ([#67](https://github.com/jellewillekes/ml-lifecycle-platform/issues/67)) ([7d63342](https://github.com/jellewillekes/ml-lifecycle-platform/commit/7d6334273e6aefe2d1ebf9cf5a8d59a297a514ac))
* **ci:** guard Docker Python version and add PR docker builds ([#59](https://github.com/jellewillekes/ml-lifecycle-platform/issues/59)) ([518788e](https://github.com/jellewillekes/ml-lifecycle-platform/commit/518788e8e8e73ed6756f4604c0c3a59d4ea16e38))
* **ci:** make workflow uv-native and standardize dependabot updates ([#17](https://github.com/jellewillekes/ml-lifecycle-platform/issues/17)) ([cef40ca](https://github.com/jellewillekes/ml-lifecycle-platform/commit/cef40caa5c9ff355e55eb1d95b14d72441ed58ae))
* **ci:** pin Python 3.11.7 for uv in GitHub Actions ([#38](https://github.com/jellewillekes/ml-lifecycle-platform/issues/38)) ([f00f853](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f00f853f5182240d40500ddef7adb8b86f393733))
* release please root config ([#27](https://github.com/jellewillekes/ml-lifecycle-platform/issues/27)) ([7fa2cea](https://github.com/jellewillekes/ml-lifecycle-platform/commit/7fa2cea63f4824e71a27e7c822e94f6bd94fed33))


### Dependencies

* **actions:** bump docker/setup-buildx-action ([#65](https://github.com/jellewillekes/ml-lifecycle-platform/issues/65)) ([493d122](https://github.com/jellewillekes/ml-lifecycle-platform/commit/493d122fae70ce0987749d319debadde6d7b3e0c))
* **actions:** bump the github-actions group with 4 updates ([#37](https://github.com/jellewillekes/ml-lifecycle-platform/issues/37)) ([f7632f8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f7632f8001f535b2e20e1414010ea5b4f93b50eb))
* **docker:** bump python from 3.11-slim to 3.14-slim ([#42](https://github.com/jellewillekes/ml-lifecycle-platform/issues/42)) ([a989897](https://github.com/jellewillekes/ml-lifecycle-platform/commit/a989897c83245b4021b79ca8a4c95c42897c4323))


### Documentation

* add production-grade README for model release platform ([f981697](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f981697ce61f3f6449c9c5195d103681eb0efc23))
* add verified current-state architecture baseline ([#40](https://github.com/jellewillekes/ml-lifecycle-platform/issues/40)) ([d84c353](https://github.com/jellewillekes/ml-lifecycle-platform/commit/d84c353d2c14f5c821adf79851f5aec796a2592c))
* freeze m0 portability charter and adrs ([#55](https://github.com/jellewillekes/ml-lifecycle-platform/issues/55)) ([5a1f0f4](https://github.com/jellewillekes/ml-lifecycle-platform/commit/5a1f0f4eb54791ef12bd7b9406aec6ee5561d3be))

## [0.4.0](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.3.1...v0.4.0) (2026-03-09)


### Features

* **local-runtime-profile-cli:** implement local profile loader and CLI ([#64](https://github.com/jellewillekes/ml-lifecycle-platform/issues/64)) ([2f2c055](https://github.com/jellewillekes/ml-lifecycle-platform/commit/2f2c0553003da16d4fc9f713723f3d4c99aef2a5))
* **runtime:** add local backend adapter interfaces ([#62](https://github.com/jellewillekes/ml-lifecycle-platform/issues/62)) ([2f3bdc8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/2f3bdc8d364e5361cd13519934c73cbd27c98433))


### Bug Fixes

* **ci:** bootstrap Python and uv in E2E workflow ([#67](https://github.com/jellewillekes/ml-lifecycle-platform/issues/67)) ([7d63342](https://github.com/jellewillekes/ml-lifecycle-platform/commit/7d6334273e6aefe2d1ebf9cf5a8d59a297a514ac))
* **ci:** guard Docker Python version and add PR docker builds ([#59](https://github.com/jellewillekes/ml-lifecycle-platform/issues/59)) ([518788e](https://github.com/jellewillekes/ml-lifecycle-platform/commit/518788e8e8e73ed6756f4604c0c3a59d4ea16e38))

## [0.3.1](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.3.0...v0.3.1) (2026-03-04)


### Bug Fixes

* **ci:** pin Python 3.11.7 for uv in GitHub Actions ([#38](https://github.com/jellewillekes/ml-lifecycle-platform/issues/38)) ([f00f853](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f00f853f5182240d40500ddef7adb8b86f393733))


### Dependencies

* **docker:** bump python from 3.11-slim to 3.14-slim ([#42](https://github.com/jellewillekes/ml-lifecycle-platform/issues/42)) ([a989897](https://github.com/jellewillekes/ml-lifecycle-platform/commit/a989897c83245b4021b79ca8a4c95c42897c4323))


### Documentation

* add verified current-state architecture baseline ([#40](https://github.com/jellewillekes/ml-lifecycle-platform/issues/40)) ([d84c353](https://github.com/jellewillekes/ml-lifecycle-platform/commit/d84c353d2c14f5c821adf79851f5aec796a2592c))
* freeze m0 portability charter and adrs ([#55](https://github.com/jellewillekes/ml-lifecycle-platform/issues/55)) ([5a1f0f4](https://github.com/jellewillekes/ml-lifecycle-platform/commit/5a1f0f4eb54791ef12bd7b9406aec6ee5561d3be))

## [0.3.0](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.2.1...v0.3.0) (2026-03-02)


### Features

* reproduce registered models from source runs ([#35](https://github.com/jellewillekes/ml-lifecycle-platform/issues/35)) ([bc98ed8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/bc98ed8bba36d920aecacccd212193c1e9617019))


### Dependencies

* **actions:** bump the github-actions group with 4 updates ([#37](https://github.com/jellewillekes/ml-lifecycle-platform/issues/37)) ([f7632f8](https://github.com/jellewillekes/ml-lifecycle-platform/commit/f7632f8001f535b2e20e1414010ea5b4f93b50eb))

## [0.2.1](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.2.0...v0.2.1) (2026-03-01)


### Bug Fixes

* release please root config ([#27](https://github.com/jellewillekes/ml-lifecycle-platform/issues/27)) ([7fa2cea](https://github.com/jellewillekes/ml-lifecycle-platform/commit/7fa2cea63f4824e71a27e7c822e94f6bd94fed33))

## [0.2.0](https://github.com/jellewillekes/ml-lifecycle-platform/compare/v0.1.0...v0.2.0) (2026-02-17)

### Features

* add release policy module and dry-run promotion gate ([#24](https://github.com/jellewillekes/ml-lifecycle-platform/issues/24)) ([23e4818](https://github.com/jellewillekes/ml-lifecycle-platform/commit/23e48188fa3309cf45c8249ec3ff264f00f8343e))

---

## Historical Release Notes

The sections above are managed by Release Please.

The section below contains the initial platform release notes.

## [0.1.0](https://github.com/jellewillekes/ml-lifecycle-platform/releases/tag/v0.1.0)

Initial Platform Release

This release introduced the core model release platform with safe promotion,
progressive delivery, reproducibility, and operational basics.

### Highlights

- Alias-based model lifecycle using MLflow aliases (`candidate`, `prod`, `champion`) instead of stages.
- Safe rollouts with canary + shadow serving modes and deterministic traffic bucketing.
- Reproducibility and governance via dataset fingerprinting, lineage metadata, promotion guardrails, and deterministic rollback.
- Production operability with CI gating, health endpoints, Prometheus metrics, and structured logging.
- Repo standards including templates, CODEOWNERS, release automation, Dependabot, and security posture.

### Core Capabilities

#### Model Release Workflow

- Alias-based promotion flow (`candidate -> prod / champion`)
  PRs: #1, #2
- Promotion safety rails (required provenance tags, rollback metadata, one-command rollback)
  PR: #11

#### Progressive Delivery

- Serving modes: `prod`, `candidate`, `canary`, `shadow`
- Deterministic bucketing and request ID propagation for traceability
  PRs: #4, #8

#### Reproducibility And Lineage

- Dataset fingerprinting and lineage metadata on model versions
  PR: #6
- Contracts and constants to prevent interface drift
  PR: #7

#### Reliability, Observability, And Operations

- CI gating with fast checks and smoke/E2E validation on `master`
  PR: #3
- Typed settings and operational endpoints (`health`, `livez`, `readyz`)
  PR: #9
- Prometheus `/metrics` and structured logging
  PR: #10

#### Developer Experience And Governance

- Pre-commit hooks for consistent formatting and linting
  PR: #5
- Repo standards: PR template, CODEOWNERS, CONTRIBUTING, Release Please, Dependabot, security/legal baseline
  PR: #12

### Included Changes

- #1 `feat: switch to alias-based MLflow releases (candidate/prod)`
- #2 `feat: alias-based release with prod/champion + docs`
- #3 `ci: add gating with fast checks and smoke on master`
- #4 `feat: canary + shadow serving`
- #5 `chore: pre-commit hooks`
- #6 `feat: dataset fingerprinting and lineage metadata`
- #7 `feat: contracts and constants`
- #8 `feat: request ID and deterministic bucketing`
- #9 `feat: platform ops (typed settings, health endpoints, E2E workflow)`
- #10 `feat: Prometheus metrics endpoint and structured logging`
- #11 `feat: promotion guardrails and deterministic rollback`
- #12 `chore: repo standards, release automation and governance`
