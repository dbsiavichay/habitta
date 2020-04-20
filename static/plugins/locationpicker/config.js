function getPosition() {
    var lon = $('#id_longitude').val();
    var lat = $('#id_latitude').val();

    if (lon && lat) setMap(lon, lat)
    else {
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(function(position) {
                setMap(position.coords.longitude, position.coords.latitude);
            });
        } else {
            setMap(-78.11685009999997, -2.2874005)
        }        
    }
}


$('#id_address, #id_latitude, #id_longitude').keydown(function (e) {
    if (e.keyCode == 13) e.preventDefault();
});

function setMap(lon, lat) {   
    var radius = $('#id_radius').val();
    
    var l = $('#inputMap').locationpicker({
        location: {
            latitude: lat,
            longitude: lon,
        },
        enableAutocomplete: true,
        enableReverseGeocode: true,
        radius: radius?radius:0,
        zoom: 14,
        inputBinding: {
            longitudeInput: $('#id_longitude'),        
            latitudeInput: $('#id_latitude'),
            radiusInput: $('#id_radius'),
            locationNameInput: $('#id_address')
        },
        addressFormat: "street_number",
        onchanged: function (currentLocation, radius, isMarkerDropped) {
            var addressComponents = $(this).locationpicker('map').location.addressComponents;            
            //console.log(currentLocation);  //latlon  
            //console.log(addressComponents);
            //updateControls(addressComponents); //Data
        }
    });
    window.l = l;
}

$(function () {
    getPosition();
});
