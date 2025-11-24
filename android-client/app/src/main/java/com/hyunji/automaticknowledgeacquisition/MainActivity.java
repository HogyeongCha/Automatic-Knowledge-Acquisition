package com.hyunji.automaticknowledgeacquisition;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.firebase.firestore.FieldValue;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.messaging.FirebaseMessaging;
import com.google.firebase.storage.FirebaseStorage;
import com.google.firebase.storage.StorageReference;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;

public class MainActivity extends AppCompatActivity {

    private FirebaseFirestore db;
    private FirebaseStorage storage;
    private TextView statusText;
    private ProgressBar progressBar;

    // 🌟 5가지 분석 모드 정의 (호경이 맞춤형)
    final String[] modes = {"📝 학습 노트", "💻 기술 뉴스", "🎨 아이디어", "📈 경제 공부", "📂 일반/기타"};
    final String[] modeKeys = {"study", "tech", "idea", "economy", "general"};

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // 1. Firebase 및 UI 초기화
        db = FirebaseFirestore.getInstance();
        storage = FirebaseStorage.getInstance();
        statusText = findViewById(R.id.statusText);
        progressBar = findViewById(R.id.progressBar);

        // 2. FCM 알림 구독 (결과 수신용)
        FirebaseMessaging.getInstance().subscribeToTopic("updates")
                .addOnCompleteListener(task -> {
                    if (!task.isSuccessful()) {
                        System.out.println("알림 구독 실패");
                    }
                });

        // 3. 안드로이드 13(Tiramisu) 이상 알림 권한 요청
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
            }
        }

        // 4. 공유하기(Intent) 수신 처리
        Intent intent = getIntent();
        String action = intent.getAction();
        String type = intent.getType();

        if (action != null && type != null) {
            // 공유하기로 실행되었을 경우 모드 선택 팝업 띄우기
            if (Intent.ACTION_SEND.equals(action) || Intent.ACTION_SEND_MULTIPLE.equals(action)) {
                showModeSelectionDialog(intent);
            }
        } else {
            statusText.setText("대기 중... \n사진이나 글을 공유해주세요.");
        }
    }

    // =========================================================
    // 🌟 Step 1: 모드 선택 팝업 (가장 먼저 실행됨)
    // =========================================================
    private void showModeSelectionDialog(Intent intent) {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("어떤 관점으로 분석할까요?");

        builder.setItems(modes, (dialog, which) -> {
            // 사용자가 선택한 모드 (which는 인덱스 번호)
            String selectedMode = modeKeys[which];
            statusText.setText("선택 모드: " + modes[which] + "\n데이터 처리 시작...");

            // 선택된 모드로 실제 업로드 진행
            processIntent(intent, selectedMode);
        });

        // 취소(뒤로가기) 시 앱 종료
        builder.setOnCancelListener(dialog -> finish());
        builder.show();
    }

    // =========================================================
    // 🌟 Step 2: 데이터 유형별 분기 처리
    // =========================================================
    private void processIntent(Intent intent, String mode) {
        String action = intent.getAction();
        String type = intent.getType();

        if (Intent.ACTION_SEND.equals(action)) {
            // 단일 데이터
            if ("text/plain".equals(type)) {
                handleSendText(intent, mode);
            } else if (type.startsWith("image/")) {
                handleSendImage(intent, mode);
            }
        } else if (Intent.ACTION_SEND_MULTIPLE.equals(action)) {
            // 다중 이미지 데이터
            if (type.startsWith("image/")) {
                handleSendMultipleImages(intent, mode);
            }
        }
    }

    // =========================================================
    // 📝 텍스트 처리
    // =========================================================
    private void handleSendText(Intent intent, String mode) {
        String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (sharedText != null) {
            statusText.setText("텍스트 업로드 중...");
            // 텍스트는 바로 DB Queue로 전송 (storagePath는 null)
            uploadToQueue("text", sharedText, null, mode, null, () -> {
                statusText.setText("전송 완료! \n(분석이 완료되면 알림이 옵니다)");
                finishAppDelay();
            });
        }
    }

    // =========================================================
    // 📸 단일 이미지 처리
    // =========================================================
    private void handleSendImage(Intent intent, String mode) {
        Uri imageUri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        if (imageUri != null) {
            statusText.setText("이미지 업로드 중...");
            uploadImageToFirebase(imageUri, mode, () -> {
                statusText.setText("전송 완료!");
                finishAppDelay();
            });
        }
    }

    // =========================================================
    // 📸📸 다중 이미지 처리 (여러 장)
    // =========================================================
    private void handleSendMultipleImages(Intent intent, String mode) {
        ArrayList<Uri> imageUris = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
        if (imageUris != null) {
            int totalCount = imageUris.size();
            AtomicInteger uploadedCount = new AtomicInteger(0); // 스레드 안전 카운터
            statusText.setText("총 " + totalCount + "장 업로드 시작...");

            for (Uri imageUri : imageUris) {
                uploadImageToFirebase(imageUri, mode, () -> {
                    // 한 장 완료될 때마다 실행
                    int current = uploadedCount.incrementAndGet();
                    statusText.setText("업로드 중... (" + current + "/" + totalCount + ")");

                    // 모두 완료되면 종료
                    if (current == totalCount) {
                        statusText.setText("모두 전송 완료!");
                        finishAppDelay();
                    }
                });
            }
        }
    }

    // =========================================================
    // ☁️ 내부 헬퍼 함수: 이미지 Storage 업로드
    // =========================================================
    private void uploadImageToFirebase(Uri imageUri, String mode, Runnable onSuccess) {
        String filename = UUID.randomUUID().toString() + ".jpg";
        String storagePath = "uploads/" + filename; // 🌟 경로 저장!

        StorageReference ref = storage.getReference().child(storagePath);

        ref.putFile(imageUri)
                .addOnSuccessListener(taskSnapshot -> {
                    // 업로드 성공 시 다운로드 URL 획득
                    ref.getDownloadUrl().addOnSuccessListener(uri -> {
                        // DB Queue에 작업 등록 (storagePath도 같이 넘김!)
                        uploadToQueue("image", filename, uri.toString(), mode, storagePath, onSuccess);
                    });
                })
                .addOnFailureListener(e -> {
                    statusText.setText("이미지 업로드 실패: " + e.getMessage());
                });
    }

    // =========================================================
    // ☁️ 내부 헬퍼 함수: Firestore Queue 등록
    // =========================================================
    private void uploadToQueue(String type, String content, String url, String mode, String storagePath, Runnable onSuccess) {
        Map<String, Object> task = new HashMap<>();
        task.put("type", type);         // image or text
        task.put("content", content);   // 텍스트 내용 or 파일명
        task.put("url", url);           // 이미지 다운로드 URL (텍스트면 null)
        task.put("mode", mode);         // 🌟 선택한 분석 모드
        task.put("status", "waiting");  // Python Brain이 감지할 상태
        task.put("createdAt", FieldValue.serverTimestamp());
        task.put("source", "android");

        // 🌟 Storage 경로가 있으면 같이 저장 (Python 삭제용)
        if (storagePath != null) {
            task.put("storagePath", storagePath);
        }

        db.collection("queue")
                .add(task)
                .addOnSuccessListener(documentReference -> {
                    if (onSuccess != null) onSuccess.run();
                })
                .addOnFailureListener(e -> {
                    statusText.setText("DB 저장 실패: " + e.getMessage());
                });
    }

    // =========================================================
    // 🚪 앱 자동 종료 (딜레이)
    // =========================================================
    private void finishAppDelay() {
        new Handler(Looper.getMainLooper()).postDelayed(this::finish, 1500);
    }
}