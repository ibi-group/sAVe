// Makes a request to Flask backend. Javascript secrets are a mess.
const requestKey = async () => {
    console.log("hey");
    const response = await fetch('http://localhost:5000/secret');
    const json = await response.json();
    console.log(await json);
    return json;

}

const loadAll=function(){

    // Open maps, as opposed to proprietary.
    L.mapquest.open = true;
    const baseLayer = L.mapquest.tileLayer('map');
    let map = L.mapquest.map('map', {
        // Centered in NYC.
        center: [40.7128, -74.0060], // 40.7128° N, 74.0060° W
        layers: baseLayer,
        zoom: 12,
        // Allows for many points to be layered with low latency.
        preferCanvas: true,
    });
    // Moves address of business to destination when marker is clicked.
    function addressToDest(e){
        document.getElementById('dest').value = e.target.options.address;
    }
    let myRenderer = L.canvas({ padding: 0.5 });
    // Getting list of locations from template.
    const myScript = document.getElementById('mapjs');
    let locations = JSON.parse(myScript.getAttribute("data"));

    const greenIcon = new L.Icon({
    iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
    });
    const greyIcon = new L.Icon({
    iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-grey.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
    });
    const blueIcon = new L.Icon({
    iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
    });
    let currentIcon = greyIcon;
    let currentText = "";
    // L.marker([51.5, -0.09], {icon: greenIcon}).addTo(map);
    if (myScript.getAttribute("businessmap")){
        // Use markers for businesses.
        for (let i = 0; i < locations.length; i += 1) {
            currentIcon = greyIcon;
            currentText = locations[i].name;
            if (locations[i].discount){
                currentIcon = blueIcon;
                currentText = (
                    locations[i].name +
                    "<br>This location has discounted rates of " +
                    locations[i].discount + "% off."
                );
            }
            if (locations[i].promotion){
                currentIcon = greenIcon;
                currentText = (
                    locations[i].name +
                    '<br><span style="color:red">LIMITED TIME ONLY</span><br>' +
                    locations[i].promotion +
                    "% off when traveling to this location!"
                );

            }
            L.marker([locations[i].latitude,locations[i].longitude],
                {
                    title: locations[i].name,
                    address: locations[i].address,
                    icon: currentIcon,
                }
            ).addTo(map).on('click', addressToDest).bindPopup(currentText);
        }
    }
    else {
        // Use circles if they're user rides.
        for (let i = 0; i < locations.length; i += 1) {
            L.circle([locations[i].origin_latitude,locations[i].origin_longitude],
                {
                    color: "blue",
                    opacity: .2,
                    radius: 100,
                    renderer: myRenderer,
                    fillOpacity: 0.2,
                    fillColor: "blue",
                }).addTo(map);
            L.circle(
                [
                    locations[i].destination_latitude,
                    locations[i].destination_longitude
                ],
                {
                    color: "red",
                    opacity: .2,
                    radius: 100,
                    renderer: myRenderer,
                    fillOpacity: 0.2,
                    fillColor: "red"
                }).addTo(map);
        }
    }

    L.control.layers({
            'Map': baseLayer
    }).addTo(map);
};

fetch('http://localhost:5000/secret').then((resp)=>resp.json()).then((resp)=>{
    L.mapquest.key=resp["mapquest"];
    loadAll();
})
