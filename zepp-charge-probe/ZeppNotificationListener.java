package org.example.zeppchargeprobe;

import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

public class ZeppNotificationListener extends NotificationListenerService {
  public static volatile ZeppNotificationListener instance;
  @Override public void onListenerConnected() {super.onListenerConnected();instance=this;}
  @Override public void onListenerDisconnected() {instance=null;super.onListenerDisconnected();}
  @Override public void onDestroy() {instance=null;super.onDestroy();}
  @Override public void onNotificationPosted(StatusBarNotification sbn) {
    // Intentionally no persistent logging, notification collection, or network transfer.
  }
}
