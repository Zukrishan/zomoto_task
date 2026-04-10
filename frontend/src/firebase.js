import { initializeApp } from "firebase/app";
import { getMessaging, getToken, onMessage } from "firebase/messaging";

const firebaseConfig = {
  apiKey: "AIzaSyDJot21fIrHajZTNfvucASagund1sBskiM",
  authDomain: "zomoto-task-cc906.firebaseapp.com",
  projectId: "zomoto-task-cc906",
  storageBucket: "zomoto-task-cc906.firebasestorage.app",
  messagingSenderId: "54995367285",
  appId: "1:54995367285:web:23f26753d7e39d4dffcf3c"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

export const requestNotificationPermission = async () => {
  try {
    const token = await getToken(messaging, { 
      vapidKey: "BHjrpJQpUz_SUoSw0rS2CXaTB5jMyQVYHuH3A5-7f9gAY7G4NOOri5ti0P_K4cnNOa7jSpDEHbcCegGByhqLCEQ" 
    });
    if (token) {
      console.log("FCM Token:", token);
      return token;
    }
  } catch (error) {
    console.error("Notification permission error:", error);
  }
  return null;
};

export default messaging;
