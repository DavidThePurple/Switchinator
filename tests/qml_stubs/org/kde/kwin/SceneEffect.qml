import QtQml
QtObject {
    default property list<QtObject> data
    property int viewActivationCount: 0
    function viewForScreen(screen) {return {screen:screen};}
    function activateView(view) {viewActivationCount++;}
    property Component delegate
    property bool visible: false
    property var configuration: ({UseTheme:true,CustomAccent:false,PrimaryColor:"#121212",SecondaryColor:"#222222",AccentColor:"#aabbcc",TextColor:"#ffffff",PreviewSize:100,SelectedScale:1.5,LayoutMode:0,Animations:true,SelectedStyle:1,StyleStrength:6,ShowBackground:false,FinishMs:360,OpenMs:240,AutoRotate:false,RotationDelay:5})
}
