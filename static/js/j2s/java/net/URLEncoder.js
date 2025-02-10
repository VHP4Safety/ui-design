Clazz.declarePackage("java.net");
(function(){
var c$ = Clazz.declareType(java.net, "URLEncoder", null);
c$.encode = Clazz.defineMethod(c$, "encode", 
function(s){
return encodeURIComponent(s);
}, "~S");
})();
;//5.0.1-v2 Mon Apr 08 08:45:17 CDT 2024
