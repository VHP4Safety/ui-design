Clazz.declarePackage("JS");
(function(){
var c$ = Clazz.decorateAsClass(function(){
this.width = 0;
this.height = 0;
Clazz.instantialize(this, arguments);}, JS, "Dimension", null);
Clazz.makeConstructor(c$, 
function(w, h){
this.set(w, h);
}, "~N,~N");
Clazz.defineMethod(c$, "set", 
function(w, h){
this.width = w;
this.height = h;
return this;
}, "~N,~N");
})();
;//5.0.1-v4 Wed Dec 11 08:23:48 CST 2024
