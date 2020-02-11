document.addEventListener('DOMContentLoaded', function () {
    var center = {'lng': -78.11685009999997, 'lat': -2.2874005};

    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {           
            center['lng'] = position.coords.longitude;
            center['lat'] = position.coords.latitude
            buildMap(center);            
        });
    }else{
        buildMap(center);
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
           map.fitBounds(place.geometry.viewport);         
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


var map;
var mapBounds;
var markers = [];
var cluster;
var infobox;

var getSearchUrl = function () {
    var url = '/api/properties/';
    var category = document.getElementById('id_search_category').value;
    var purpose = document.getElementById('id_search_purpose').value;
    var address = document.getElementById('ac_address').value;
    var radio = document.getElementById('range').value;
    var lat = map.center.lat();
    var lng = map.center.lng();
    url = url + '?radio='+radio

    if (!category && !purpose && !address) return url + '&lat='+lat+'&lng='+lng;

    url+='&';
    if (category) url+= 'category='+category+'&';
    if (purpose) url+= 'purpose='+purpose+'&';
    if (address) url+= 'address='+address+'&';
    else url+= 'lat='+lat+'&lng='+lng;
    return url;
}

var getLocations = function(map, url) { 
    $.get(url, function (data) {
        renderCards(data);
        buildMarkers(data, map);
    });
}

var getInfoBoxTemplate = function(location){    
    var template = '<div class="map-popup-wrap">'+
                '<div class="map-popup">'+
                    '<div class="infoBox-close"><i class="fa fa-times"></i></div>'+
                    '<div class="map-popup-category">'+location.category+'</div>'+
                    '<a href="'+location.url+'" class="listing-img-content fl-wrap"><img src="'+location.cover+'" alt=""></a>'+
                    '<div class="listing-content fl-wrap">'+
                        '<div class="card-popup-raining map-card-rainting" data-staRrating="'+location.stars+'">'+
                            '<span class="map-popup-reviews-count">( '+location.reviews+' comentarios )</span>'+
                        '</div>'+
                        '<div class="listing-title fl-wrap">'+
                            '<h4><a href='+location.url+">"+location.purpose+'</a></h4>'+
                            '<span class="map-popup-location-info"><i class="fa fa-map-marker"></i>'+location.address+'</span>'+
                            '<span class="map-popup-location-phone"><i class="fa fa-phone"></i>'+location.phone+'</span>'+
                        '</div>'+
                    '</div>'+
                '</div>'+
            '</div>';
    
    return template;
}

var buildInfoBox = function (locations, map) {        
    var currentLocation;    
    var container=document.createElement("div");
    container.className="map-box";  
    var options = {
        content:container,
        disableAutoPan:true,
        alignBottom:true,
        maxWidth:300,
        pixelOffset:new google.maps.Size(-140,-45),
        zIndex:null,
        boxStyle:{width:'260px'},
        closeBoxMargin:'0',
        closeBoxURL:"",
        infoBoxClearance:new google.maps.Size(1,1),
        isHidden:false,
        pane:'floatPane',
        enableEventPropagation:false
    };

    for (var index in locations){               
        infobox = new InfoBox;
        google.maps.event.addListener(infobox, 'domready',function(){cardRaining()});

        
        google.maps.event.addListener(locations[index].marker, 'click', function(marker,index){
            return function(){          
                infobox.setOptions(options);                
                container.innerHTML=getInfoBoxTemplate(locations[index]);
                infobox.open(map,marker);               
                currentLocation = marker.id;
                
                map.panTo(marker.getPosition());
                map.panBy(0,-180);
                google.maps.event.addListener(infobox,'domready',function(){
                    document.querySelector('.infoBox-close').addEventListener('click', function(e) {
                        e.preventDefault();
                        infobox.close();
                    });
                })
            }
        }(locations[index].marker,index))   
          
    }

    document.querySelector('.nextmap-nav').addEventListener('click', function(e){       
        e.preventDefault();
        map.setZoom(16);
        var next = currentLocation + 1;
        if(next < locations.length) google.maps.event.trigger(locations[next].marker,'click');
        else google.maps.event.trigger(locations[0].marker,'click');
    });

    document.querySelector('.prevmap-nav').addEventListener('click', function(e){
        e.preventDefault();
        map.setZoom(16);
        var prev = currentLocation - 1;
        if(prev > -1) google.maps.event.trigger(locations[prev].marker,'click');
        else google.maps.event.trigger(locations[locations.length-1].marker,'click');
    });
}

var destroyMarkers = function(map) {
    if (cluster) {
        cluster.removeMarkers(markers, map);
        map.setZoom(14);
        markers = [];       
    }
}

var buildMarkers = function(locations, map) {
    destroyMarkers(map);
    filtered_locations = []
    if (!locations.length) return;

    var icon = {        
        url:"/static/images/marker.png",        
        anchor:new google.maps.Point(24,50),
    };  

    for (var index=0;index<locations.length;index++) {
        var location = locations[index];  
        if (location['latitude'] != 0 && location['longitude'] != 0) {
            var marker = new google.maps.Marker({
                animation:google.maps.Animation.DROP,
                position:new google.maps.LatLng(location['latitude'],location['longitude']),
                icon:icon,
                id:index
            });
            markers.push(marker);
            location['marker'] = marker;
            filtered_locations.push(location)
        }         
        
    }
    
    buildInfoBox(filtered_locations, map);           

    cluster = new MarkerClusterer(map, markers, {
        imagePath:"images/",
        styles:[{url:"",height:40,width:40}],
        minClusterSize:2
    }); 
}

var buildControls = function(map){
    var container = document.createElement('div');      
    container.index = 1;
    map.controls[google.maps.ControlPosition.RIGHT_CENTER].push(container);
    container.style.padding='5px';
    var controls = document.createElement('div');
    container.appendChild(controls);

    var zoomIn = document.createElement('div');
    zoomIn.className = 'mapzoom-in';
    controls.appendChild(zoomIn);

    var zoomOut = document.createElement('div');
    zoomOut.className = 'mapzoom-out';
    controls.appendChild(zoomOut);

    google.maps.event.addDomListener(zoomIn, 'click', function() {
        map.setZoom(map.getZoom()+1);
    });
    google.maps.event.addDomListener(zoomOut, 'click', function(){
        map.setZoom(map.getZoom()-1);
    });
}

var buildMap = function (center) {
    var zoom=document.getElementById('map-main').getAttribute('data-map-zoom');
    var scroll=document.getElementById('map-main').getAttribute('data-map-scroll'); 


    if(zoom) zoom=parseInt(zoom);
    else zoom=14;

    if(scroll) scroll=parseInt(scroll);
    else scroll=false;
            
    map = new google.maps.Map(
        document.getElementById("map-main"),
        {
            zoom:zoom,
            scrollwheel:scroll,
            center:center,
            mapTypeId:google.maps.MapTypeId.ROADMAP,
            zoomControl:false,
            mapTypeControl:true,
            scaleControl:false,
            panControl:false,
            navigationControl:false,
            streetViewControl:false,
            animation:google.maps.Animation.BOUNCE,
            gestureHandling:"cooperative",
            styles:[{featureType:"administrative",elementType:"labels.text.fill",stylers:[{color:"#444444"}]}]
        }
    );

    var marker = new google.maps.Marker({
        position: center,
        map: map,
        title: 'Mi ubicación.'
    });

    buildControls(map);
    getLocations(map, getSearchUrl());

    google.maps.event.addDomListener(window, 'resize', function() {     
        google.maps.event.trigger(map,'resize');
        map.setCenter(map.getCenter());
    }); 
}

var renderCards = function(locations) {
    var container = document.getElementById('locations');
    container.innerHTML = ''
    if(!locations) return;
    for (var i in locations){
        container.insertAdjacentHTML('beforeend', locations[i].list_card)
    }

    $('.listing-item').on('click', function () {
        window.location.href = $(this).data('url');
    });
}