Clazz.declarePackage("J.shapebio");
Clazz.load(["J.shapebio.BioShapeCollection"], "J.shapebio.Rockets", null, function(){
var c$ = Clazz.declareType(J.shapebio, "Rockets", J.shapebio.BioShapeCollection);
Clazz.overrideMethod(c$, "initShape", 
function(){
this.setTurn();
});
Clazz.defineMethod(c$, "setTurn", 
function(){
this.madTurnRandom = 500;
});
});
;//5.0.1-v4 Wed Dec 11 08:23:48 CST 2024
