Copy paste this file in ```/etc/systemd/system/eclipseDiscordBot.service```


```
[Unit]
Description=Discord bot for eclipse calculator
After=network.target
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=1
User=pi
ExecStart=/usr/bin/python3 /home/pi/Eclipse/BoardgameCalculatorDiscordBot/discordbot.py

[Install]
WantedBy=multi-user.target
```


Then enter

```systemctl start eclipseDiscordBot.server```

```systemctl enable eclipseDiscordBot.server```
