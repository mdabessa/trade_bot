import os
from math import ceil
from time import sleep

from dhooks import File, Webhook


class Logger:
    def __init__(self, fname: str = '../logs/log.txt') -> None:
        self.fname = fname
        if self.fname:
            directory = os.path.dirname(fname)
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                except:
                    pass

        try:
            os.remove(self.fname)
        except:
            pass

    def __call__(self, info: str) -> None:
        info = str(info)
        print(info + '\n')
        if self.fname:
            with open(self.fname, 'a') as f:
                f.write(info + '\n\n')


class DiscordLogger(Logger):
    def __init__(
        self,
        webhook_url: str,
        avatar_url: str = None,
        webhook_username: str = 'Logger',
        fname: str = './log.txt',
    ) -> None:
        super().__init__(fname=fname)
        self.hook = Webhook(
            webhook_url, username=webhook_username, avatar_url=avatar_url
        )

    def send(self, msg: str, file: str = None) -> None:
        msg = str(msg)
        if file != None:
            file = File(file, name='file.txt')
            self.hook.send(msg, file=file)
        else:
            self.hook.send(msg)

    def __call__(
        self, info: str, mention_id: int = None, file: bool = False
    ) -> None:
        info = str(info)
        super().log(info)

        if mention_id != None:
            self.send(f'<@{mention_id}>')

        if file:
            with open('temp_log.txt', 'w') as f:
                f.write(info)

            self.send(msg='Arquivo:', file='./temp_log.txt')

            os.remove('temp_log.txt')

        else:
            info += ' '
            divs = ceil(len(info) / 2000)
            parts = int(len(info) / divs)
            time = 0.5 if divs > 1 else 0
            for i in range(0, divs):
                try:
                    msg = info[i * parts : (i + 1) * parts]
                    self.send(msg)
                    sleep(time)

                except Exception as e:
                    super().log(e)
                    self.send('Erro no logger:')
                    self.send(e)
