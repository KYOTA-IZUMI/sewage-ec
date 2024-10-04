import csv
import datetime
import time
from collections import deque

import ambient
import serial
import os
from dotenv import load_dotenv
import serial.tools.list_ports


def list_serial_ports():
    """利用可能なシリアルポートの一覧を取得"""
    return [port.device for port in serial.tools.list_ports.comports()]

def select_serial_port():
    """利用可能なポートを表示し、ユーザーに選択させる"""
    ports = list_serial_ports()
    
    if not ports:
        print("利用可能なシリアルポートがありません。")
        return None
    
    print("利用可能なポート:")
    for i, port in enumerate(ports):
        print(f"{i + 1}: {port}")
    
    try:
        choice = int(input("ポート番号を選択してください: ")) - 1
        if 0 <= choice < len(ports):
            return ports[choice]
        else:
            print("無効な選択です。")
    except ValueError:
        print("数字を入力してください。")
    
    return None

class SaveAsCSV:
    def __init__(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f'output_{timestamp}.csv'
        self.data_queue = deque()
        # ファイルを作成しヘッダーを書く
        with open(self.filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Data"])  # ヘッダー
    
    def add(self, data):
        """データを1行追加してCSVに保存"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, data])
        self.data_queue.append([timestamp, data])
    
    def write(self, num_rows):
        """最新のデータを指定した行数分取得"""
        with open(self.filename, mode='r') as file:
            reader = csv.reader(file)
            rows = list(reader)[-num_rows:]  # 最新の指定行数分を取得
        for row in rows:
            print(row)

def send_to_ambient(voltage, w_strength):
    load_dotenv()
    channel_id = os.getenv("AMBIENT_CHANNEL_ID")
    write_key = os.getenv("AMBIENT_WRITE_KEY")
    am = ambient.Ambient(channel_id, write_key)
    r = am.send({'d1': voltage, 'd2': w_strength})
    if r.status_code == 200:
        print("Data was sent successfully.")
    else:
        print(f"Failed to send data. Status code: {r.status_code}")
        
        
def main():
    # シリアルポートを選択
    selected_port = select_serial_port()
    if selected_port:
        # シリアルポートを開く
        ser = serial.Serial(selected_port, 38400, timeout=1)
        # CSVファイルを作成
        csv_saver = SaveAsCSV()
        last_sent_time = time.time()

        try:
            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').rstrip()
                    print(f"Received: {line}")
                    # lineをintに変換できる場合だけ追加
                    try:
                        data = int(line)
                        csv_saver.add(data)  # データをCSVに追加
                    except ValueError:
                        print(f"無効なデータ: {line}")
                    
                    current_time = time.time()
                    if current_time - last_sent_time >= 30: # Ambientは一日30秒程度間隔をあけないといけない
                        send_to_ambient(data, 9999)
                        last_sent_time = current_time
        except KeyboardInterrupt:
            print("プログラムを終了します。")
        finally:
            ser.close()
    else:
        print("プログラムを終了します。")

if __name__ == "__main__":
    main()