import './shared/device-polyfill'
import { MessageBuilder } from './shared/message'
App({
  globalData: {messageBuilder: null},
  onCreate() {
    // Zepp OS 1.0 requires a handshake and framed packets.
    const info=hmApp.packageInfo()
    const builder=new MessageBuilder({appId:info.appId})
    this.globalData.messageBuilder=builder
    builder.connect()
    console.log('Mini BatteryLink official ZeppOS 1.0 bridge created appId='+info.appId)
  },
  onDestroy(){
    if(this.globalData.messageBuilder) {
      try {this.globalData.messageBuilder.disConnect()}catch(e){console.log('Mini bridge teardown '+String(e))}
    }
  }
})
