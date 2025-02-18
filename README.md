# CatchFile

## Описание  
CatchFile — **децентрализованное хранилище файлов**, которое позволяет синхронизировать их между устройствами **без центрального сервера**, используя **peer-to-peer** (P2P) технологию, аналогичную торрентам. Аналог Dropbox.

-  **Полный контроль над файлами** — никаких облаков, только устройства пользователя.  
-  ~~**Конечное шифрование (E2EE)** — файлы передаются в зашифрованном виде.~~  
-  **Автоматическая синхронизация** — файлы обновляются между устройствами автоматически.  
-  **Минимальные системные требования** — работает даже на слабых устройствах.  

##  Как это работает  
1. **Добавление папки в синхронизацию** — указываешь корневую директорию, и файлы начинают распространяться между подключёнными устройствами.  
2. **Подключение устройств через magnet-ссылки** — получатель вводит только ссылку - и больше никаких действий.  
3. **Локальная база данных** — отслеживает файлы и их расположение.  
4. **Общая P2P-база** — содержит только хэши файлов и статусы (активен, удалён).  
~~5. **Шифрование** — передача файлов защищена, данные остаются конфиденциальными.~~

##  Системные требования

### Минимальные:
- **CPU**: 1 GHz, 1 ядро
- **RAM**: 512 MB

### Рекомендуемые:
- **CPU**: 2 GHz, 2+ ядра
- **RAM**: 2 GB

##  Установка  
Пока нет стабильного релиза, но если хочешь попробовать:  

```bash
git clone https://github.com/nichney/catchFile.git
cd catchFile  
python3 -m venv venv  
source venv/bin/activate  # (или venv\Scripts\activate на Windows)  
pip install -r requirements.txt  
python main.py  
```


##  Планируется добавить  
- Шифрование файлов при передаче
- Кроссплатформенность

##  Лицензия  
This software is licensed under the GNU Affero General Public License v3.0 (AGPLv3).  

For commercial use outside AGPL terms, a separate commercial license is available.  
Contact cyberstatar@gmail.com for more details.
