# Git Workflow для проекта SFMShop

## Использованные команды Git
- git init - инициализация репозитория
- git add - добавление файлов в staging area
- git commit - сохранение версии с описанием
- git push - отправка кода на GitHub
- git pull - получение изменений с GitHub
- git status - просмотр состояния репозитория
- git log - просмотр истории коммитов
- git branch - создание и просмотр веток
- git checkout - переключение между ветками
- git merge - слияние веток
- git rebase - перенос коммитов поверх другой ветки
- git stash - временное сохранение изменений
- git diff - сравнение изменений между ветками

## Созданные ветки
- main - основная ветка проекта
- feature/add-discount-system - система скидок в классе Product
- feature/add-email-validation - валидация email в классе User
- feature/add-inventory-management - управление складом в классе Product
- feature/add-shipping - метод расчёта доставки
- feature/test-conflict - тестирование конфликтов
- feature/test-stash - тестирование git stash
- feature/test-rebase - тестирование git rebase

## Разрешённые конфликты
- Конфликт в src/models/product.py при слиянии feature/test-conflict в main
  Причина: оба изменили метод get_total_price
  Решение: оставлена объединённая версия метода

- Конфликт в src/models/product.py при слиянии main в feature/add-shipping
  Причина: в main добавлен get_weight, в ветке calculate_shipping
  Решение: объединены оба метода в файле

## Стратегия работы с ветками
1. Обновить main перед началом работы: git pull
2. Создать feature-ветку: git checkout -b feature/название
3. Работать в ветке, делать частые коммиты
4. Обновлять ветку из main: git merge main
5. Разрешать конфликты если есть
6. Отправить ветку: git push -u origin feature/название
7. Создать Pull Request на GitHub
8. После проверки командой слить в main

## Важные правила
- Никогда не пушить напрямую в main
- Делать осмысленные сообщения коммитов
- Обновлять ветку из main регулярно
- Добавлять ненужные файлы в .gitignore