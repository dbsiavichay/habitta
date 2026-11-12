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
        getLocations(getSearchUrl());
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
                var key = (window.LARBIT_CONFIG || {}).googleGeocodingKey;
                if (!key) return;
                var url = 'https://maps.googleapis.com/maps/api/geocode/json?latlng='+lat+','+lng+'&key='+encodeURIComponent(key);
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
    var minPrice = document.getElementById('minPrice').value;
    var maxPrice = document.getElementById('maxPrice').value;

    if(minPrice || maxPrice){
        if(!minPrice) minPrice = 0
        if(!maxPrice) maxPrice = 999999999
        url = url + '?min_price='+minPrice+'&max_price='+maxPrice
    }

    if (!category && !purpose && !address) return url;
    url+='&';
    if (category) url+= 'category='+encodeURIComponent(category)+'&';
    if (purpose) url+= 'purpose='+encodeURIComponent(purpose)+'&';
    if (address) url+= 'address='+encodeURIComponent(address)+'&';
    return url;
}

var getLocations = function(center) {
    var url = getSearchUrl(); 
    $.get(url, function (data) {
        renderCards(data);
    });
}

var renderCards = function(locations) {    
    var container = document.getElementById('locations');
    container.innerHTML = '';
    if(!locations) return;
    for (var i in locations){
        container.insertAdjacentHTML('beforeend', locations[i].list_card)
    }
    $('.listing-item').on('click', function () {
        window.location.href = $(this).data('url');
    });
}