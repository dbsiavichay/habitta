!function($){
	"use strict";

	//Para buscar por punto
    /* if ("geolocation" in navigator) {
		var center = {'lng': -78.11685009999997, 'lat': -2.2874005};
        navigator.geolocation.getCurrentPosition(function(position) {           
            center['lng'] = position.coords.longitude;
            center['lat'] = position.coords.latitude
            console.log(center)          
        });
    } */

	//Show a single position 

	var mapMarker={		
		url:"/static/images/marker.png",		
		anchor:new google.maps.Point(24,50),
	};

	var map=document.getElementById("singleMap");
	void 0!==map&&null!=map&&google.maps.event.addDomListener(window,"load",function() {
		var cords={
			lng:$("#singleMap").data("longitude"),
			lat:$("#singleMap").data("latitude")
		},
		map=new google.maps.Map(document.getElementById("singleMap"),{
			zoom:14,
			center:cords,
			scrollwheel:!1,
			zoomControl:!1,
			mapTypeControl:!1,
			scaleControl:!1,
			panControl:!1,
			navigationControl:!1,
			streetViewControl:!1,
			styles:[{featureType:"landscape",elementType:"all",stylers:[{color:"#f2f2f2"}]}]
		}),

		t=(new google.maps.Marker({position:cords,map:map,icon:mapMarker,title:"Nuestra ubicación"}),document.createElement("div"));

		new function(e,map){
			t.index=1,
			map.controls[google.maps.ControlPosition.RIGHT_CENTER].push(t),
			e.style.padding="5px";
			var controls=document.createElement("div");
			e.appendChild(controls);
			var zoomIn=document.createElement("div");
			zoomIn.className="mapzoom-in",controls.appendChild(zoomIn);
			var zoomOut=document.createElement("div");
			zoomOut.className="mapzoom-out",controls.appendChild(zoomOut),
			google.maps.event.addDomListener(zoomIn,"click",function(){map.setZoom(map.getZoom()+1)}),
			google.maps.event.addDomListener(zoomOut,"click",function(){map.setZoom(map.getZoom()-1)})
		}(t,map)
	})
}(this.jQuery);