# astrbot_plugin_telegram

一个让 Astrbot 支持 Telegram 平台的插件。

> 欢迎任何贡献 ❤️

## 使用

安装好插件后，刷新管理面板，在 `消息平台`->`消息平台适配器` 点击加号，即可看到 `telegram`，点击添加即可配置。

在群聊时，前面加一个 `/` 即可触发机器人。如 `/help`, `/你好啊`

加入临时的速率限制功能，可在tg_message_adapter.py设置self.rate_limit调整，默认值为30s

> [!TIP]
> 当更新这个插件后，请在 配置页 直接点击保存配置以全量重启，否则不会生效
> when updated this plugin, please directly click the save button in the Config Page to fully restart the AstrBot, or the update may not make effect
