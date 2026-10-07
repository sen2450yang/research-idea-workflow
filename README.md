# 科研创新与研究设计 Skill

**标识：`research-idea-workflow` · 版本：1.0.0 · 制作日期：2026-10-07**

从研究背景、领域脉络和文献比较出发，形成原创解释，核查真实创新增量，再落成能够支持、修正或推翻假说的研究方案。

本包保留上一版十阶段完整正文，并将其转为可调用的执行流程。它不会因为缺少直接先例而提前淘汰构想，也不会把大胆构思写成已经验证的事实。科学评价与资源可行性分开，反证检索与审稿式检查用于改进路线，而不是机械压低创新性。

## 先看哪里

[SKILL.md](SKILL.md) 是给AI读取的入口。[完整十阶段正文](references/workflow-complete.md) 保留此前的全部优化内容。[内容覆盖对照](references/coverage-map.md) 说明原六步、十阶段及新增内容之间的关系。[调用示例](examples/usage.md) 可直接复制使用。

```text
research-idea-workflow/
├── SKILL.md                    主入口、触发范围与执行原则
├── README.md                   使用与安装说明
├── agents/openai.yaml          可选显示信息与默认提示
├── references/                 完整流程、阶段指南、证据和评议规则
├── assets/templates/           8份Markdown模板＋1份状态JSON
├── examples/usage.md           不同任务范围的调用示例
├── scripts/                    可选初始化工具、包检查及工具测试
├── evals/scenarios.json         行为验收场景，非已执行结果
├── VALIDATION.md                本次实际检查结果和未验证范围
└── manifest.json               文件清单、字节数与SHA-256
```

一个主Skill管理同一条研究流程，细节按需加载。没有将十阶段拆成互相竞争的十个自动触发Skill，也不要求每次单一问题都完整执行十阶段。

## 在Codex中本地使用

本包采用带 `SKILL.md` 的Agent Skills目录格式，而不是已发布插件。规范与Codex目录发现方式见文末[技术依据](#技术依据)。[T1][T2]

解压后，把完整的 `research-idea-workflow` 文件夹放入已授权研究项目的技能目录；不要只复制入口文件：

```text
<你的研究项目目录>/.agents/skills/research-idea-workflow/SKILL.md
```

这是项目目录用法。Codex文档也列出了用户级目录 `$HOME/.agents/skills`；是否采用用户级安装应由你决定，本包不自动写入任何位置。确认当前宿主加载到了该Skill后，可在支持的Codex界面中显式调用：[T2]

```text
使用 $research-idea-workflow。
结合我已经提供的研究背景与材料，先比较领域证据，再形成有价值的研究构想。
保留大胆假说，随后核查最接近工作、反证和竞争解释，按本次范围推进。
```

不同客户端的发现、刷新和选择方式应以实际界面为准。具体显示信息由 `agents/openai.yaml` 提供；不使用该配置的宿主仍可读取标准入口。[T1][T3]

本次只生成并交付压缩包，**没有安装到你的电脑、没有修改系统或Codex配置，也没有验证你的客户端能否自动触发**。Mori及Agentcodex原有的项目、路径和授权限制不因使用本包而改变。

## 作为普通对话材料使用

在尚未加载Skill的对话环境中，可以将解压后的相关文件作为材料提供给AI，明确要求先读取 `SKILL.md`，再按本轮范围读取对应参考文件。只上传ZIP或只在消息里提及名称，不能据此认定宿主已经完成持久安装。

首次任务无需重新输入已经提供的背景。只有领域、材料和本轮目标确实缺失时才补充；不必先填写一整套空表。

## 可选：建立研究工作记录

Skill本体不依赖Python。下面的工具需要Python 3.10或更新版本，仅使用标准库，不访问网络，不安装软件，不做文献搜索或数据分析。

在解压后的Skill根目录运行以下命令；将占位路径替换为已授权且已存在的父目录：

```bash
python scripts/init_project.py --destination "<已授权父目录>/my-study" --title "研究主题" --mode full --dry-run
python scripts/init_project.py --destination "<已授权父目录>/my-study" --title "研究主题" --mode full
```

`--dry-run`只打印计划，不创建目录。正式运行只创建一个新的任务目录，将模板复制进去并写入主题、时间和阶段状态；目标已经存在时拒绝写入。不会覆盖旧课题或自动选择本地路径。

`--mode`支持 `full`、`landscape`、`ideation`、`novelty`、`review`、`pilot`、`protocol`。这些模式只提供初始范围标记，不能代替研究者或AI核查实际前提。脚本会复制完整模板集，单阶段任务通常直接选用所需模板即可。

空白模板、计划以及状态文件都不是研究结果。只有完成相应实际工作并核查结果，才能将阶段改为 `completed`。

## 包检查与行为验收

```bash
python scripts/validate_skill.py . --check-manifest
python scripts/test_tooling.py
```

第一条检查本包的结构、入口元数据约定、内部文件链接、十阶段覆盖、JSON、Python语法和文件哈希；不是通用YAML解析器或官方认证工具。第二条在临时测试目录中检查初始化、拒绝覆盖、干运行、路径及错误处理等行为，测试结束清理它自己创建的临时目录。

本次实际结果见 [VALIDATION.md](VALIDATION.md)。`evals/scenarios.json` 中的场景供在目标宿主中测试Skill触发和研究行为：执行场景后，将真实回答与预期行为及失败信号对照记录。这些模型场景在本次打包中没有实际运行，不能将场景文件存在当作测试通过。

本包也没有开展任何具体领域的文献检索、创新性验证、样本分析或实验。已有流程是研究工作规范，不是已经验证有效的科研成功保证。

## 技术依据

以下资料于2026-10-07查阅；技术文档只用于核对Skill结构和使用方式，没有被整篇复制进本包。安装方式随宿主版本可能调整。

[T1] Agent Skills：Specification。用于核对 `SKILL.md`、必需元数据、目录命名及按需参考资源。

```text
https://agentskills.io/specification
```

[T2] OpenAI：Build skills。原Codex Skills地址在本次访问时转向官方Build skills页面。用于核对目录发现位置和显式调用方式。

```text
https://developers.openai.com/codex/skills
https://learn.chatgpt.com/docs/build-skills
```

[T3] OpenAI Codex：`skill-creator/references/openai_yaml.md`。用于核对可选显示字段、默认提示与调用策略。

```text
https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/references/openai_yaml.md
```

本包中的科研流程正文来自本次对话的上一版优化内容，执行指南、模板和脚本围绕该内容编写，没有复用其他项目的私有资料。
