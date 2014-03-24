
## Android flow

First create the publishpoint call:

    POST /nba/servlets/publishpoint HTTP/1.1
    User-Agent: Android Mobile
    Accept-Encoding: gzip, deflate
    Content-Length: 52
    Content-Type: application/x-www-form-urlencoded
    Host: watch.nba.com
    Connection: Keep-Alive
    Cookie: JSESSIONID=32221~4E71AA90DD0B9A0D6465B469445A3BB7; locale=en_US; nbasubs=true

    type=game&id=0021301036&gt=condensed&format=xml&nt=1HTTP/1.1 200 OK
    Server: nginx/1.2.6
    Date: Mon, 24 Mar 2014 17:41:44 GMT
    Content-Type: text/xml;charset=UTF-8
    Content-Length: 393
    Connection: keep-alive
    Keep-Alive: timeout=5
    Pragma: no-cache
    Cache-Control: no-cache
    Expires: 1

    <?xml version="1.0" encoding="UTF-8"?><result><path><![CDATA[http://nlds120.cdnak.neulion.com/nlds_vod/nba/vod/2014/03/22/21301036/ff3741/2_21301036_mia_nop_2013_h_condensed_1_android.mp4.m3u8?nltid=nba&nltdt=8&nltnt=1&uid=1433543&hdnea=expires%3D1395683024%7Eaccess%3D%2Fnlds_vod%2Fnba%2Fvod%2F2014%2F03%2F22%2F21301036%2Fff3741%2F*%7Emd5%3D4ec38c3c8611d3e101184d81db51e790]]></path></result>


This will give us the URL for the video under result => path. No cookies are needed for the following request:

    GET /nlds_vod/nba/vod/2014/03/22/21301036/ff3741/2_21301036_mia_nop_2013_h_condensed_1_android.mp4.m3u8?nltid=nba&nltdt=8&nltnt=1&uid=1433543&hdnea=expires%3D1395683024%7Eaccess%3D%2Fnlds_vod%2Fnba%2Fvod%2F2014%2F03%2F22%2F21301036%2Fff3741%2F*%7Emd5%3D4ec38c3c8611d3e101184d81db51e790 HTTP/1.1
    Host: nlds120.cdnak.neulion.com
    Connection: keep-alive
    Cookie: nlqptid=nltid=nba&nltdt=8&nltnt=1&uid=1433543&hdnea=expires%3D1395683024%7Eaccess%3D%2Fnlds_vod%2Fnba%2Fvod%2F2014%2F03%2F22%2F21301036%2Fff3741%2F*%7Emd5%3D4ec38c3c8611d3e101184d81db51e790;
    User-Agent: Android
    Accept-Encoding: gzip,deflate

    HTTP/1.1 200 OK
    Server: NeuLion Adaptive Streaming Server
    Last-Modified: Sun, 23 Mar 2014 07:12:24 GMT
    Content-Type: application/vnd.apple.mpegurl
    Content-Length: 545
    Cache-Control: max-age=65830
    Expires: Tue, 25 Mar 2014 11:59:05 GMT
    Date: Mon, 24 Mar 2014 17:41:55 GMT
    Connection: keep-alive
    Set-Cookie: nlqptid=nltid=nba&nltdt=8&nltnt=1&uid=1433543&hdnea=expires%3D1395683024%7Eaccess%3D%2Fnlds_vod%2Fnba%2Fvod%2F2014%2F03%2F22%2F21301036%2Fff3741%2F*%7Emd5%3D4ec38c3c8611d3e101184d81db51e790; path=/; domain=.neulion.com

    #EXTM3U
    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=400000
    2_21301036_mia_nop_2013_h_condensed_1_400_android.mp4.m3u8
    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1200000
    2_21301036_mia_nop_2013_h_condensed_1_1200_android.mp4.m3u8
    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=800000
    2_21301036_mia_nop_2013_h_condensed_1_800_android.mp4.m3u8
    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=240000
    2_21301036_mia_nop_2013_h_condensed_1_240_android.mp4.m3u8
    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=150000
    2_21301036_mia_nop_2013_h_condensed_1_150_android.mp4.m3u8

This gives the player the HLS playlist -and- a cookie which is needed for its playback. then typically we will see a request for a specific quality:

    GET /nlds_vod/nba/vod/2014/03/22/21301036/ff3741/2_21301036_mia_nop_2013_h_condensed_1_400_android.mp4.m3u8 HTTP/1.1
    Host: nlds120.cdnak.neulion.com
    Connection: keep-alive
    Cookie: nlqptid=nltid=nba&nltdt=8&nltnt=1&uid=1433543&hdnea=expires%3D1395683024%7Eaccess%3D%2Fnlds_vod%2Fnba%2Fvod%2F2014%2F03%2F22%2F21301036%2Fff3741%2F*%7Emd5%3D4ec38c3c8611d3e101184d81db51e790
    User-Agent: Android
    Accept-Encoding: gzip,deflate

    HTTP/1.1 200 OK
    Last-Modified: Sun, 23 Mar 2014 04:29:41 GMT
    Server: NeuLion Adaptive Streaming Server
    Content-Type: application/vnd.apple.mpegurl
    Content-Length: 7786
    Expires: Mon, 24 Mar 2014 17:41:56 GMT
    Cache-Control: max-age=0, no-cache, no-store
    Pragma: no-cache
    Date: Mon, 24 Mar 2014 17:41:56 GMT
    Connection: keep-alive

    #EXTM3U
    #EXT-X-TARGETDURATION:10
    #EXT-X-KEY:METHOD=AES-128,URI="http://nlsk.neulion.com/nlsk1/hls/securekey?id=120&url=/nlds_vod/nba/vod/2014/03/22/21301036/ff3741/2_21301036_mia_nop_2013_h_condensed_1_400.mp4/m3u8.key"

And before the playback starts a request for the decryption key:

    GET /nlsk1/hls/securekey?id=120&url=/nlds_vod/nba/vod/2014/03/22/21301036/ff3741/2_21301036_mia_nop_2013_h_condensed_1_400.mp4/m3u8.key HTTP/1.1
    Host: nlsk.neulion.com
    Connection: keep-alive
    Cookie: nlstck=32053; nlqptid=nltid=nba&nltdt=8&nltnt=1&uid=1433543&hdnea=expires%3D1395683024%7Eaccess%3D%2Fnlds_vod%2Fnba%2Fvod%2F2014%2F03%2F22%2F21301036%2Fff3741%2F*%7Emd5%3D4ec38c3c8611d3e101184d81db51e790
    User-Agent: Android
    Accept-Encoding: gzip,deflate

    HTTP/1.1 200 OK
    Server: nginx/1.2.6
    Date: Mon, 24 Mar 2014 17:41:58 GMT
    Content-Length: 16
    Connection: keep-alive
    Keep-Alive: timeout=5
    Set-Cookie: X-NL-SK-nlds_vod-nba-vod-2014-03-22-21301036-ff3741=FJsmSPq%2Fb%2FuViQzC9xnWA8nweJA8dOmLIV6sTQzPY91%2B5fcMxMCDLUuzlzBH71jNzxkWiuZgTwTOXvgyqTJ%2FDBF63Awjrqu1tBoVSQ3EtgEdWz8k9wtWQRqC4Y%2Fcy9IUFhr5FzQ6z6lzpNEIn9HduA%3D%3D; Domain=.neulion.com; Expires=Mon, 24-Mar-2014 17:47:58 GMT; Path=/
    Access-Control-Allow-Origin: *
    Access-Control-Allow-Credentials: true
    p3p: CP="CAO PSA OUR"
    Content-Disposition: attachment; filename="m3u8.key"

    ..l~.'..usxx^...


The fact that now encryption is used and this decryption key request is needed is why the previous solution broke.
