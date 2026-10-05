
package com.example.hm10app

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothStatusCodes
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.util.ArrayDeque
import java.util.UUID

@SuppressLint("MissingPermission")
class MainActivity : AppCompatActivity() {

    private val hm10Service =
        UUID.fromString("0000ffe0-0000-1000-8000-00805f9b34fb")

    private val hm10Write =
        UUID.fromString("0000ffe1-0000-1000-8000-00805f9b34fb")

    private val nordicService =
        UUID.fromString("6e400001-b5a3-f393-e0a9-e50e24dcca9e")

    private val nordicWrite =
        UUID.fromString("6e400002-b5a3-f393-e0a9-e50e24dcca9e")

    private lateinit var pythonButton: Button
    private lateinit var connectButton: Button
    private lateinit var sendButton: Button
    private lateinit var messageInput: EditText
    private lateinit var statusText: TextView
    private lateinit var stopButton: Button

    private val handler = Handler(Looper.getMainLooper())
    private var scanning = false

    private var connection: BluetoothGatt? = null
    private var tx: BluetoothGattCharacteristic? = null
    private var writeType =
        BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT

    private val pending = ArrayDeque<ByteArray>()

    private val adapter: BluetoothAdapter? by lazy {
        (getSystemService(BLUETOOTH_SERVICE)
                as BluetoothManager).adapter
    }

    private val permissionsLauncher =
        registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions()
        ) { results ->
            if (results.values.all { it }) {
                startConnection()
            } else {
                showStatus("Bluetooth permission denied")
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        pythonButton = findViewById(R.id.pythonButton)

        connectButton = findViewById(R.id.connectButton)
        sendButton = findViewById(R.id.sendButton)
        messageInput = findViewById(R.id.messageInput)
        statusText = findViewById(R.id.statusText)
        pythonButton = findViewById(R.id.pythonButton)
        stopButton = findViewById(R.id.stopButton)

        stopButton.setOnClickListener {
            sendText("STOP")
        }

        connectButton.setOnClickListener {
            if (hasPermissions()) {
                startConnection()
            } else {
                permissionsLauncher.launch(requiredPermissions())
            }
        }


        sendButton.setOnClickListener {
            val text = messageInput.text.toString()
            if (text.isNotBlank()) {
                sendText(text)
            }
        }

        pythonButton.setOnClickListener {
            sendPythonTest()
        }
    }

    private fun sendPythonTest() {
        Thread(Runnable {
            try {
                // Запускаем Python, если он ещё не запущен.
                if (!Python.isStarted()) {
                    Python.start(
                        AndroidPlatform(getApplicationContext())
                    )
                }

                // Вызываем функцию из ble_test.py.
                val message = Python.getInstance()
                    .getModule("ble_test")
                    .callAttr("get_message")
                    .toString()

                Log.d("PYTHON_BLE", "Python returned: " + message)

                runOnUiThread(Runnable {

                    sendText(message);
                    // Место подключения показано ниже.
                    Toast.makeText(
                        this,
                        "Python: " + message,
                        Toast.LENGTH_SHORT
                    ).show()
                })
            } catch (e: Exception) {
                Log.e("PYTHON_BLE", "Python error", e)
            }
        }).start()
    }

    private fun requiredPermissions(): Array<String> =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_CONNECT
            )
        } else {
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        }

    private fun hasPermissions(): Boolean =
        requiredPermissions().all {
            ContextCompat.checkSelfPermission(this, it) ==
                    PackageManager.PERMISSION_GRANTED
        }

    private fun showStatus(message: String) {
        statusText.text = message
    }

    // Scan for the HM-10

    private val scanTimeout = Runnable {
        if (scanning) {
            stopScan()
            connectButton.isEnabled = true
            showStatus("HM-10 not found")
        }
    }

    private val scanCallback = object : ScanCallback() {

        override fun onScanResult(
            callbackType: Int,
            result: ScanResult
        ) {
            val name = result.scanRecord?.deviceName
                ?: result.device.name
                ?: ""

            if (
                result.device.address.equals(
                    "20:91:48:C5:7A:0E",
                    ignoreCase = true
                )
            ) {
                runOnUiThread {
                    if (!scanning) return@runOnUiThread

                    stopScan()
                    showStatus("Connecting to $name...")

                    connection = result.device.connectGatt(
                        this@MainActivity,
                        false,
                        gattCallback,
                        BluetoothDevice.TRANSPORT_LE
                    )
                }
            }
        }

        override fun onScanFailed(errorCode: Int) {
            runOnUiThread {
                stopScan()
                connectButton.isEnabled = true
                showStatus("Scan failed: $errorCode")
            }
        }
    }

    private fun startConnection() {
        if (!hasPermissions()) return

        val bluetooth = adapter

        if (bluetooth == null) {
            showStatus("Bluetooth unavailable")
            return
        }

        if (!bluetooth.isEnabled) {
            showStatus("Turn on Bluetooth and try again")
            return
        }

        stopScan()
        connection?.close()
        connection = null
        tx = null
        pending.clear()


        pythonButton.isEnabled = false
        sendButton.isEnabled = false
        pythonButton.isEnabled = false
        stopButton.isEnabled = false
        connectButton.isEnabled = false
        showStatus("Searching for HM-10...")

        val scanner = bluetooth.bluetoothLeScanner

        if (scanner == null) {
            connectButton.isEnabled = true
            showStatus("BLE scanner unavailable")
            return
        }

        scanning = true
        scanner.startScan(scanCallback)
        handler.postDelayed(scanTimeout, 10_000)
    }

    private fun stopScan() {
        handler.removeCallbacks(scanTimeout)

        if (scanning) {
            scanning = false

            if (hasPermissions()) {
                adapter?.bluetoothLeScanner
                    ?.stopScan(scanCallback)
            }
        }
    }

    // Connect and discover the serial characteristic

    private val gattCallback = object : BluetoothGattCallback() {

        override fun onConnectionStateChange(
            gatt: BluetoothGatt,
            status: Int,
            newState: Int
        ) {
            if (status == BluetoothGatt.GATT_SUCCESS &&
                newState == BluetoothProfile.STATE_CONNECTED
            ) {
                runOnUiThread {
                    showStatus("Discovering services...")
                }
                gatt.discoverServices()
            } else {
                gatt.close()

                runOnUiThread {
                    if (connection === gatt) {
                        connection = null
                        tx = null
                        pending.clear()
                        sendButton.isEnabled = false
                        stopButton.isEnabled = false
                        pythonButton.isEnabled = false
                        connectButton.isEnabled = true
                        showStatus("Disconnected ($status)")
                    }
                }
            }
        }

        override fun onServicesDiscovered(
            gatt: BluetoothGatt,
            status: Int
        ) {
            val characteristic = if (
                status == BluetoothGatt.GATT_SUCCESS
            ) {
                gatt.getService(hm10Service)
                    ?.getCharacteristic(hm10Write)
                    ?: gatt.getService(nordicService)
                        ?.getCharacteristic(nordicWrite)
            } else null

            runOnUiThread {
                if (connection !== gatt) return@runOnUiThread

                if (characteristic == null) {
                    showStatus("HM-10 serial service not found")
                    connectButton.isEnabled = true
                    gatt.disconnect()
                    return@runOnUiThread
                }

                val properties = characteristic.properties

                writeType = when {
                    properties and
                            BluetoothGattCharacteristic.PROPERTY_WRITE != 0 ->
                        BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT

                    properties and
                            BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE != 0 ->
                        BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE

                    else -> {
                        showStatus("Characteristic is not writable")
                        connectButton.isEnabled = true
                        gatt.disconnect()
                        return@runOnUiThread
                    }
                }

                tx = characteristic
                connectButton.isEnabled = true
                connectButton.text = "Reconnect"
                sendButton.isEnabled = true
                pythonButton.isEnabled = true
                stopButton.isEnabled = true
                showStatus("Connected to HM-10")
            }
        }

        override fun onCharacteristicWrite(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
            status: Int
        ) {
            runOnUiThread {
                if (connection !== gatt) return@runOnUiThread

                if (status == BluetoothGatt.GATT_SUCCESS) {
                    sendNextPacket()
                } else {
                    pending.clear()
                    sendButton.isEnabled = true
                    showStatus("Send failed: $status")
                }
            }
        }
    }

    // Send text in packets of up to 20 bytes

    private fun sendText(text: String) {
        if (connection == null || tx == null) {
            showStatus("Connect first")
            return
        }

        val data = "$text\n".toByteArray(Charsets.UTF_8)

        pending.clear()

        data.toList().chunked(20).forEach { packet ->
            pending.addLast(packet.toByteArray())
        }

        sendButton.isEnabled = false
        showStatus("Sending...")
        sendNextPacket()
    }

    private fun sendNextPacket() {
        val gatt = connection
        val characteristic = tx

        if (gatt == null || characteristic == null) {
            pending.clear()
            sendButton.isEnabled = false
            return
        }

        if (pending.isEmpty()) {
            sendButton.isEnabled = true
            showStatus("Text sent")
            return
        }

        val packet = pending.removeFirst()

        val started = if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
        ) {
            gatt.writeCharacteristic(
                characteristic,
                packet,
                writeType
            ) == BluetoothStatusCodes.SUCCESS
        } else {
            characteristic.writeType = writeType
            characteristic.setValue(packet)
            gatt.writeCharacteristic(characteristic)
        }

        if (!started) {
            pending.clear()
            sendButton.isEnabled = true
            showStatus("Could not start BLE write")
        }
    }

    override fun onDestroy() {
        stopScan()
        connection?.close()
        connection = null
        super.onDestroy()
    }
}
