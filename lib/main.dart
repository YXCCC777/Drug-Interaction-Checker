import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:image_picker/image_picker.dart';
import 'package:image_cropper/image_cropper.dart';

// 準備一個全域變數來裝手機的鏡頭清單
late List<CameraDescription> cameras;

Future<void> main() async {
  // 確保 Flutter 核心已經準備好
  WidgetsFlutterBinding.ensureInitialized();
  
  try {
    // 取得手機上所有可用的相機 (前鏡頭、後鏡頭)
    cameras = await availableCameras();
  } on CameraException catch (e) {
    debugPrint('相機錯誤: ${e.code}, ${e.description}');
  }

  runApp(const MaterialApp(
    debugShowCheckedModeBanner: false,
    home: WelcomePage(), // 你的第一頁
  ));
}

// --- 1. 歡迎頁面 ---
class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('藥物系統')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SizedBox(
              width: 200,
              height: 50,
              child: ElevatedButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const LoginPage())), child: const Text('登入')),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: 200,
              height: 50,
              child: ElevatedButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const RegisterPage())), child: const Text('註冊')),
            ),
          ],
        ),
      ),
    );
  }
}

// --- 2. 登入頁面 ---
class LoginPage extends StatelessWidget {
  const LoginPage({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('登入')),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            const TextField(decoration: InputDecoration(labelText: '帳號', border: OutlineInputBorder())),
            const SizedBox(height: 15),
            const TextField(obscureText: true, decoration: InputDecoration(labelText: '密碼', border: OutlineInputBorder())),
            const SizedBox(height: 30),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const MainAppPage())), child: const Text('登入進入系統')),
            ),
          ],
        ),
      ),
    );
  }
}

// --- 3. 註冊頁面 ---
class RegisterPage extends StatelessWidget {
  const RegisterPage({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('註冊帳號')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            const TextField(decoration: InputDecoration(labelText: '名字', border: OutlineInputBorder())),
            const SizedBox(height: 15),
            const TextField(decoration: InputDecoration(labelText: '帳號', border: OutlineInputBorder())),
            const SizedBox(height: 15),
            const TextField(obscureText: true, decoration: InputDecoration(labelText: '密碼', border: OutlineInputBorder())),
            const SizedBox(height: 15),
            const TextField(obscureText: true, decoration: InputDecoration(labelText: '再次輸入密碼', border: OutlineInputBorder())),
            const SizedBox(height: 30),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const ProfilePage())),
                style: ElevatedButton.styleFrom(backgroundColor: Colors.teal, foregroundColor: Colors.white),
                child: const Text('完成註冊'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// --- 4. 個人資料頁面 ---
class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});
  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  String selectedGender = '男';
  final TextEditingController groupCodeController = TextEditingController();

  void showFinalSuccessDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Icon(Icons.check_circle, color: Colors.green, size: 60),
        content: const Text('註冊手續已全部完成！\n現在將引導您前往登入頁面。', textAlign: TextAlign.center),
        actions: [
          Center(
            child: TextButton(
              onPressed: () {
                Navigator.pop(context); 
                Navigator.pushAndRemoveUntil(
                  context, 
                  MaterialPageRoute(builder: (context) => const LoginPage()),
                  (route) => false
                );
              },
              child: const Text('登入'),
            ),
          ),
        ],
      ),
    );
  }

  void showGroupCodeDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: const Text('加入群組'),
        content: TextField(
          controller: groupCodeController,
          decoration: const InputDecoration(
            hintText: "請輸入群組代碼",
            border: UnderlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context); 
              showFinalSuccessDialog(); 
            },
            child: const Text('確定'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('填寫個人資料')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('基本資料', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.teal)),
            const SizedBox(height: 20),
            const TextField(decoration: InputDecoration(labelText: '暱稱', border: OutlineInputBorder())),
            const SizedBox(height: 20),
            const Text('性別', style: TextStyle(fontSize: 16)),
            Row(
              children: [
                Radio(value: '男', groupValue: selectedGender, onChanged: (val) => setState(() => selectedGender = val!)),
                const Text('男'),
                const SizedBox(width: 20),
                Radio(value: '女', groupValue: selectedGender, onChanged: (val) => setState(() => selectedGender = val!)),
                const Text('女'),
              ],
            ),
            const SizedBox(height: 20),
            const TextField(decoration: InputDecoration(labelText: '其他資訊 1', border: OutlineInputBorder())),
            const SizedBox(height: 15),
            const TextField(decoration: InputDecoration(labelText: '其他資訊 2', border: OutlineInputBorder())),
            const SizedBox(height: 15),
            const TextField(decoration: InputDecoration(labelText: '其他資訊 3', border: OutlineInputBorder())),
            const SizedBox(height: 40),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: const Text('註冊成功'),
                      content: const Text('是否需要加入藥物討論群組？'),
                      actions: [
                        TextButton(
                          onPressed: () {
                            Navigator.pop(context); 
                            showFinalSuccessDialog(); 
                          }, 
                          child: const Text('否')
                        ),
                        TextButton(
                          onPressed: () {
                            Navigator.pop(context); 
                            showGroupCodeDialog(); 
                          }, 
                          child: const Text('是')
                        ),
                      ],
                    ),
                  );
                },
                style: ElevatedButton.styleFrom(backgroundColor: Colors.blueAccent, foregroundColor: Colors.white),
                child: const Text('註冊完成'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// --- 5. 主功能頁面 (包含底部導覽列) ---
class MainAppPage extends StatefulWidget {
  const MainAppPage({super.key});

  @override
  State<MainAppPage> createState() => _MainAppPageState();
}

class _MainAppPageState extends State<MainAppPage> {
  int _selectedIndex = 2; // 預設一進來先跳到中間第 3 格的「藥單加入」(索引值為 2)

  static const List<Widget> _pages = <Widget>[
    Center(child: Text('提醒設定頁面', style: TextStyle(fontSize: 24))),
    Center(child: Text('我的藥袋頁面', style: TextStyle(fontSize: 24))),
    AddPrescriptionPage(), // 獨立出來的「藥單加入」相機頁面
    Center(child: Text('設定頁面', style: TextStyle(fontSize: 24))),
    Center(child: Text('個人資料頁面', style: TextStyle(fontSize: 24))),
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('藥物辨識主系統'),
        automaticallyImplyLeading: false, 
      ),
      body: _pages[_selectedIndex], 
      
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed, 
        items: const <BottomNavigationBarItem>[
          BottomNavigationBarItem(icon: Icon(Icons.alarm), label: '提醒設定'),
          BottomNavigationBarItem(icon: Icon(Icons.medical_services), label: '我的藥袋'),
          BottomNavigationBarItem(icon: Icon(Icons.document_scanner), label: '藥單加入'),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: '設定'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: '個人資料'),
        ],
        currentIndex: _selectedIndex, 
        selectedItemColor: Colors.teal, 
        unselectedItemColor: Colors.grey, 
        onTap: _onItemTapped, 
      ),
    );
  }
}

// --- 獨立的「藥單加入」相機頁面積木 (StatefulWidget) ---
class AddPrescriptionPage extends StatefulWidget {
  const AddPrescriptionPage({super.key});

  @override
  State<AddPrescriptionPage> createState() => _AddPrescriptionPageState();
}

class _AddPrescriptionPageState extends State<AddPrescriptionPage> {
  CameraController? _controller;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    if (cameras.isNotEmpty) {
      _controller = CameraController(cameras[0], ResolutionPreset.high);
      _controller!.initialize().then((_) {
        if (!mounted) return;
        setState(() {}); 
      }).catchError((Object e) {
        if (e is CameraException) {
          debugPrint('相機初始化失敗: ${e.description}');
        }
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  // 從相簿選擇圖片
  Future<void> _pickImageFromGallery() async {
    final XFile? image = await _picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      _cropImage(image.path);
    }
  }

  // 拍照
  Future<void> _takePicture() async {
    if (_controller == null || !_controller!.value.isInitialized) return;
    if (_controller!.value.isTakingPicture) return;

    try {
      XFile file = await _controller!.takePicture();
      _cropImage(file.path);
    } catch (e) {
      debugPrint('拍照失敗: $e');
    }
  }

  // 裁切圖片
// 裁切圖片
  Future<void> _cropImage(String filePath) async {
    try {
      CroppedFile? croppedFile = await ImageCropper().cropImage(
        sourcePath: filePath,
        // 最新版要把比例設定放進 uiSettings 裡面
        uiSettings: [
          AndroidUiSettings(
            toolbarTitle: '裁切藥單', 
            toolbarColor: Colors.teal, 
            toolbarWidgetColor: Colors.white, 
            initAspectRatio: CropAspectRatioPreset.original,
            lockAspectRatio: false,
            // 🌟 Android 的比例設定放這裡 🌟
            aspectRatioPresets: [
              CropAspectRatioPreset.original,
              CropAspectRatioPreset.square,
              CropAspectRatioPreset.ratio4x3,
            ],
          ), 
          IOSUiSettings(
            title: '裁切藥單',
            // 🌟 iOS 的比例設定放這裡 🌟
            aspectRatioPresets: [
              CropAspectRatioPreset.original,
              CropAspectRatioPreset.square,
              CropAspectRatioPreset.ratio4x3,
            ],
          ),
        ],
      );

      if (croppedFile != null) {
        debugPrint('圖片裁切完成！檔案路徑: ${croppedFile.path}');
        _showIdentifyingDialog();
      }
    } catch (e) {
      debugPrint('裁切圖片失敗: $e');
    }
  }

  // 顯示正在辨識中畫面
// --- 更新版：顯示正在辨識中畫面 (加入自動模擬等待) ---
  void _showIdentifyingDialog() {
    showDialog(
      context: context,
      barrierDismissible: false, // 強制使用者等待
      builder: (BuildContext context) {
        return AlertDialog(
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: const [
              CircularProgressIndicator(color: Colors.teal),
              SizedBox(height: 20),
              Text("正在進行 AI 辨識...", style: TextStyle(fontSize: 16)),
              SizedBox(height: 10),
              Text("請稍候，正在向伺服器分析影像", style: TextStyle(color: Colors.grey, fontSize: 12)),
            ],
          ),
        );
      },
    );

    // 🌟 這裡模擬連線到 AI 伺服器的延遲時間 (設定為 2.5 秒)
    Future.delayed(const Duration(milliseconds: 2500), () {
      if (!mounted) return;
      Navigator.pop(context); // 1. 時間到，自動關閉轉圈圈視窗
      _showResultDialog();    // 2. 緊接著彈出辨識結果視窗！
    });
  }

  // --- 新增：辨識結果確認視窗 ---
  void _showResultDialog() {
    showDialog(
      context: context,
      barrierDismissible: false, // 必須按下正確或錯誤才能關閉
      builder: (BuildContext context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
          title: const Row(
            children: [
              Icon(Icons.fact_check, color: Colors.teal),
              SizedBox(width: 10),
              Text('辨識結果確認', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('系統在您的藥單上找到以下藥品：', style: TextStyle(fontSize: 15)),
              const SizedBox(height: 15),
              
              // 模擬列出辨識出來的藥品 (這裡以後可以換成組員回傳的真實資料)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.teal.withOpacity(0.1), // 淺綠色底色
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.teal.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: const [
                    Text('1. 普拿疼 (Panadol) 500mg', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    Text('2. 阿莫西林 (Amoxicillin) 250mg', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    Text('3. 胃酸中和劑 (Antacid)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
              const SizedBox(height: 15),
              const Text('請問以上結果是否正確？', style: TextStyle(color: Colors.redAccent, fontSize: 14, fontWeight: FontWeight.bold)),
            ],
          ),
          
          // 下半部的兩個按鈕 (正確 vs 錯誤)
          actionsAlignment: MainAxisAlignment.spaceEvenly, // 讓按鈕平均分配空間
          actions: [
            // 錯誤按鈕
            ElevatedButton.icon(
              onPressed: () {
                Navigator.pop(context); // 關閉視窗
                // TODO: 之後可以在這裡加入「手動修改藥品」或「重新拍攝」的邏輯
                debugPrint("使用者點擊：錯誤！(可能需要手動修正)");
              },
              icon: const Icon(Icons.close),
              label: const Text('錯誤'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: Colors.redAccent,
                side: const BorderSide(color: Colors.redAccent), // 紅色邊框
              ),
            ),
            
            // 正確按鈕
            ElevatedButton.icon(
              onPressed: () {
                Navigator.pop(context); // 關閉視窗
                // TODO: 之後可以在這裡把資料存進資料庫，並跳轉到「我的藥袋」頁面
                debugPrint("使用者點擊：正確！(準備將藥單加入個人紀錄)");
                
                // 可以加一個成功的小提示
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('✅ 藥單已成功加入！'), backgroundColor: Colors.teal),
                );
              },
              icon: const Icon(Icons.check),
              label: const Text('正確'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        );
      },
    );
  }
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text(
            '請將藥單對準框內',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.teal),
          ),
          const SizedBox(height: 20),
          
          // Stack 疊層積木：相機畫面 + 相簿按鈕
          Stack(
            children: [
              // 第 1 層：相機預覽框
              Container(
                width: 300,
                height: 400,
                decoration: BoxDecoration(
                  color: Colors.black, 
                  borderRadius: BorderRadius.circular(20), 
                  border: Border.all(color: Colors.teal, width: 3), 
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(17), 
                  child: (_controller != null && _controller!.value.isInitialized)
                      ? CameraPreview(_controller!)
                      : const Center(child: CircularProgressIndicator(color: Colors.teal)),
                ),
              ),
              
              // 第 2 層：相簿按鈕
              Positioned(
                bottom: 15, 
                left: 15,   
                child: Container(
                  decoration: const BoxDecoration(
                    color: Colors.white, 
                    shape: BoxShape.circle, 
                    boxShadow: [
                      BoxShadow(color: Colors.black26, blurRadius: 4, offset: Offset(0, 2)) 
                    ]
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.photo_library),
                    color: Colors.teal, 
                    iconSize: 28,
                    onPressed: _pickImageFromGallery, 
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 30),
          
          // 開始掃描按鈕
          SizedBox(
            width: 200,
            height: 55,
            child: ElevatedButton.icon(
              onPressed: _takePicture, 
              icon: const Icon(Icons.document_scanner_outlined),
              label: const Text('開始掃描', style: TextStyle(fontSize: 20)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(30), 
                ),
                elevation: 5, 
              ),
            ),
          ),
        ],
      ),
    );
  }
}
