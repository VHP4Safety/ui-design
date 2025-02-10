Clazz.declarePackage("JM");
Clazz.load(["JM.MinObject"], "JM.MinPosition", null, function(){
var c$ = Clazz.declareType(JM, "MinPosition", JM.MinObject);
Clazz.makeConstructor(c$, 
function(data, ddata){
Clazz.superConstructor (this, JM.MinPosition, []);
this.data = data;
this.ddata = ddata;
}, "~A,~A");
});
;//5.0.1-v4 Wed Dec 11 08:23:48 CST 2024
