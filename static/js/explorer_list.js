document.addEventListener('DOMContentLoaded', function () {
    var center = {'lng': -78.11685009999997, 'lat': -2.2874005};

    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {           
            center['lng'] = position.coords.longitude;
            center['lat'] = position.coords.latitude
            getLocations(center);            
        });
    }else{
        getLocations(center);
    }

    document.getElementById('search').addEventListener('click', function () {       
        getLocations(map, getSearchUrl());
    });

    var autocompleteAddress = document.getElementById('ac_address');    
    var autocomplete = new google.maps.places.Autocomplete(autocompleteAddress);    
    autocomplete.addListener('place_changed', function() {
        var place = autocomplete.getPlace();
        if (place.geometry) {
           //mapBounds = place.geometry.viewport;
           document.getElementById('search').click();
        }                
    });


    document.querySelector('.loc-act').addEventListener('click', function (e) {
        e.preventDefault();
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(function(position) {           
                var lng = position.coords.longitude;
                var lat = position.coords.latitude
                var url = 'https://maps.googleapis.com/maps/api/geocode/json?latlng='+lat+','+lng+'&key=AIzaSyDjnbmaDZ4HPsRJQC9oDHOp6PjIdPsYr8I';
                $.get(url, function (response) {
                    if (response.status=='OK') {
                        var address = response.results[1].formatted_address
                        document.querySelector('.qodef-archive-places-search').value = address;                 
                    }
                });             
            });
        }
    });              
});


document.addEventListener('DOMContentLoaded', function () {
    var band;

    var setClicksProperties = function () {
        var items = document.querySelectorAll('.geodir-category-listing');
        items.forEach(function (elem) {
            elem.addEventListener('click', function () {
                url = window.location.origin + this.dataset.url;
                window.location.assign(url);
            });
        });     
        if (items.length) clearInterval(band);
    }

    band = setInterval(setClicksProperties, 500);
    
});

var getSearchUrl = function () {
    var url = '/api/properties/';
    var category = document.getElementById('id_search_category').value;
    var purpose = document.getElementById('id_search_purpose').value;
    var address = document.getElementById('ac_address').value;

    if (!category && !purpose && !address) return url;

    url+='?';
    if (category) url+= 'category='+category+'&';
    if (purpose) url+= 'purpose='+purpose+'&';
    if (address) url+= 'address='+address+'&';
    return url;
}

var getLocations = function(center) {
    var url = getSearchUrl(); 
    $.get(url, function (data) {
        renderCards(data);
    });
}

var renderCards = function(locations) {
    console.log(locations)
    container = document.getElementById('locations');
    if(!locations) return;
    for (var i in locations){
        container.insertAdjacentHTML('beforeend', locations[i].list_card)
    }
}