importScripts("https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js");

firebase.initializeApp({
    apiKey: "AIzaSyDJot21fIrHajZTNfvucASagund1sBskiM",
  authDomain: "zomoto-task-cc906.firebaseapp.com",
  projectId: "zomoto-task-cc906",
  storageBucket: "zomoto-task-cc906.firebasestorage.app",
  messagingSenderId: "54995367285",
  appId: "1:54995367285:web:23f26753d7e39d4dffcf3c"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification;
  self.registration.showNotification(title, {
    body,
    icon: "/logo192.png"
  });
});
