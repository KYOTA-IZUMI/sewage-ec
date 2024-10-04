import csv
import datetime
import time
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
        return ports[choice] if 0 <= choice < len(ports) else None
    except ValueError:
        return None

class SaveAsCSV:
    def __init__(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f'output_{timestamp}.csv'
        with open(self.filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Data"])

    def add(self, data):
        """データをCSVに保存"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, data])

def send_to_ambient(voltage, w_strength):
    """Ambientにデータを送信"""
    load_dotenv()
    am = ambient.Ambient(os.getenv("AMBIENT_CHANNEL_ID"), os.getenv("AMBIENT_WRITE_KEY"))
    r = am.send({'d1': voltage, 'd2': w_strength})
    print("Data was sent successfully." if r.status_code == 200 else f"Failed to send data. Status code: {r.status_code}")

def process_line(line):
    """受信したデータを解析し、電波強度と電気伝導度を抽出"""
    if line.startswith(";U;"):
        try:
            # セミコロンで区切ってデータを抽出
            parts = line.split(';')
            # 電波強度と電気伝導度の位置にあるデータを取得
            signal_strength = int(parts[5])  # 例：183
            conductivity = int(parts[7])  # 例：0
            print(f"Signal strength: {signal_strength}, Conductivity: {conductivity}")
            return signal_strength, conductivity
        except (ValueError, IndexError) as e:
            print(f"データ解析エラー: {e}")
            return None, None
    else:
        print(f"無効なフォーマット: {line}")
        return None, None

def main():
    selected_port = select_serial_port()
    if not selected_port:
        print("プログラムを終了します。")
        return

    ser = serial.Serial(selected_port, 38400, timeout=1)
    csv_saver = SaveAsCSV()
    last_sent_time = time.time()

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                print(f"Received: {line}")

                signal_strength, conductivity = process_line(line)
                if signal_strength is not None and conductivity is not None:
                    csv_saver.add(f"Signal: {signal_strength}, Conductivity: {conductivity}")  # データをCSVに追加
                    if time.time() - last_sent_time >= 30:  # 30秒ごとに送信
                        send_to_ambient(signal_strength, conductivity)
                        last_sent_time = time.time()
    except KeyboardInterrupt:
        print("プログラムを終了します。")
    finally:
        ser.close()

if __name__ == "__main__":
    main()