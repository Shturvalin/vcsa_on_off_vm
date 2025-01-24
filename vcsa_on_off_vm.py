import requests
import time
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

# Игнорируем предупреждения о незащищённых HTTPS-запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройки подключения к vCenter
vcenter_server = 'https://10.10.203.92'  # URL vCenter сервера
username = 'administrator@vsphere.local'  # Имя пользователя для подключения
password = 'QAZ123wsx!@#'  # Рекомендуется использовать безопасные методы хранения паролей
vm_ids = ['vm-1001', 'vm-1002', 'vm-1007', 'vm-1008', 'vm-1009', 'vm-1038', 'vm-1039', 'vm-1040', 'vm-1041', 'vm-1042',
          'vm-1043', 'vm-1044']  # Список ID виртуальных машин
action_interval = 10  # Интервал в секундах между действиями (включение/выключение)
action_duration = 60  # Продолжительность работы виртуальной машины перед выключением
iterations = 3000  # Количество итераций для включения/выключения ВМ


def get_auth_token():
    """Получаем токен аутентификации для работы с API vCenter."""
    url = f"{vcenter_server}/rest/com/vmware/cis/session"
    response = requests.post(url, auth=(username, password), verify=False)
    if response.status_code == 200:
        return response.json()['value']  # Возвращаем токен
    else:
        raise Exception(f"Failed to get auth token: {response.status_code} - {response.text}")


def list_vms(token):
    """Получаем список всех виртуальных машин на vCenter."""
    url = f"{vcenter_server}/rest/vcenter/vm"
    headers = {
        'vmware-api-session-id': token  # Заголовок с токеном аутентификации
    }
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()['value']  # Возвращаем список ВМ
    else:
        raise Exception(f"Failed to list VMs: {response.status_code} - {response.text}")


def get_vm_power_state(token, vm_id):
    """Получаем состояние питания конкретной виртуальной машины."""
    url = f"{vcenter_server}/rest/vcenter/vm/{vm_id}"
    headers = {
        'vmware-api-session-id': token  # Заголовок с токеном аутентификации
    }
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        vm_info = response.json()
        if 'value' in vm_info and 'power_state' in vm_info['value']:
            return vm_info['value']['power_state']  # Возвращаем состояние питания ВМ
        else:
            raise Exception(f"'power_state' not found in VM info: {vm_info}")
    else:
        raise Exception(f"Failed to get VM power state: {response.status_code} - {response.text}")


def power_on_vm(token, vm_id):
    """Включаем виртуальную машину по её ID."""
    url = f"{vcenter_server}/rest/vcenter/vm/{vm_id}/power/start"
    headers = {
        'vmware-api-session-id': token  # Заголовок с токеном аутентификации
    }
    response = requests.post(url, headers=headers, verify=False)
    if response.status_code == 204:
        print(f"VM {vm_id} powered on successfully.")  # Успешное включение
    elif response.status_code == 200:
        print(f"Включили ВМ {vm_id} OK.")
    else:
        raise Exception(f"Отказ включения ВМ {vm_id}: {response.status_code} - {response.text}")


def power_off_vm(token, vm_id):
    """Выключаем виртуальную машину по её ID."""
    url = f"{vcenter_server}/rest/vcenter/vm/{vm_id}/power/stop"
    headers = {
        'vmware-api-session-id': token  # Заголовок с токеном аутентификации
    }
    response = requests.post(url, headers=headers, verify=False)
    if response.status_code == 204:
        print(f"VM {vm_id} powered off successfully.")  # Успешное выключение
    elif response.status_code == 200:
        print(f"Выключили ВМ {vm_id} OK.")
    else:
        raise Exception(f"Failed to power off VM {vm_id}: {response.status_code} - {response.text}")


def manage_vms(token):
    """Управляем виртуальными машинами: включаем и выключаем их в цикле."""
    for _ in range(iterations):  # Повторяем заданное количество итераций
        with ThreadPoolExecutor() as executor:  # Создаем пул потоков для параллельного выполнения
            futures = {}
            # Включаем все ВМ
            for vm_id in vm_ids:
                futures[executor.submit(power_on_vm, token, vm_id)] = vm_id

            # Ждем завершения всех задач включения
            for future in as_completed(futures):
                vm_id = futures[future]  # Получаем ID ВМ из futures
                try:
                    future.result()  # Проверяем на наличие исключений в выполнении задачи
                except Exception as e:
                    print(f"Error powering on VM {vm_id}: {e}")

            time.sleep(action_duration)  # Ждем заданное время работы виртуальных машин

            # Выключаем все ВМ
            futures.clear()  # Очищаем словарь futures для следующего действия
            for vm_id in vm_ids:
                futures[executor.submit(power_off_vm, token, vm_id)] = vm_id

            # Ждем завершения всех задач выключения
            for future in as_completed(futures):
                vm_id = futures[future]  # Получаем ID ВМ из futures
                try:
                    future.result()  # Проверяем на наличие исключений в выполнении задачи
                except Exception as e:
                    print(f"Error powering off VM {vm_id}: {e}")

            time.sleep(action_interval)  # Ждем перед следующим циклом


def main():
    """Основная функция для запуска программы."""
    try:
        token = get_auth_token()  # Получаем токен аутентификации
        vms = list_vms(token)  # Получаем список всех ВМ
        print("Доступные ВМ:")
        for vm in vms:
            print(f"ID: {vm['vm']}, Name: {vm['name']}")  # Выводим информацию о доступных ВМ

        manage_vms(token)  # Запускаем управление ВМ

    except Exception as e:
        print(f"An error occurred: {e}")  # Обрабатываем исключения и выводим сообщения об ошибках


if __name__ == "__main__":
    main()  # Запускаем основную функцию при выполнении скрипта
