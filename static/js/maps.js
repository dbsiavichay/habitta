!function(e){
	"use strict";

	var mapCenter = new google.maps.LatLng(-2.2874005, -78.11685009999997)

    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {
        	mapCenter = new google.maps.LatLng(position.coords.latitude, position.coords.longitude)            
        });
    }        
    
	var n={		
		url:"/static/images/marker.png",		
		anchor:new google.maps.Point(24,50),
	};


	var o=document.getElementById("map-main");

	void 0!==o&&null!=o&&google.maps.event
		.addDomListener(window, 'load', function() {
			function getMapPopup(e,n,o,a,t,i,l,s){
				return '<div class="map-popup-wrap"><div class="map-popup"><div class="infoBox-close"><i class="fa fa-times"></i></div><div class="map-popup-category">'+n+'</div><a href="'+e+'" class="listing-img-content fl-wrap"><img src="'+o+'" alt=""></a> <div class="listing-content fl-wrap"><div class="card-popup-raining map-card-rainting" data-staRrating="'+l+'"><span class="map-popup-reviews-count">( '+s+' reviews )</span></div><div class="listing-title fl-wrap"><h4><a href='+e+">"+a+'</a></h4><span class="map-popup-location-info"><i class="fa fa-map-marker"></i>'+t+'</span><span class="map-popup-location-phone"><i class="fa fa-phone"></i>'+i+"</span></div></div></div></div>"
			}


			var a = [];
			var url = '/realty/finder/';
			e.get(url, function (data) {
				console.log(data);
				a.push([getMapPopup("#","Departamento","/static/images/all/1.jpg","En renta","9443 Fairview Ave, North Bergen, NJ","+38099231212","4","11"),40.67386831,-74.10438536,11,n])
				a.push([getMapPopup("#","Departamento","/static/images/all/1.jpg","En renta","9443 Fairview Ave, North Bergen, NJ","+38099231212","4","11"),40.67386831,-74.10438536,11,n])
			});			

			var t=e("#map-main").attr("data-map-zoom"),
			i=e("#map-main").attr("data-map-scroll");
			if(void 0!==t&&!1!==t) var l=parseInt(t);
			else l=14;
			if(void 0!==i&&!1!==i) var s=parseInt(i);
			else s=!1;
			e(".nextmap-nav").on("click",function(e){
				e.preventDefault(),
				g.setZoom(14);
				var n=r;
				n+1<v.length?google.maps.event.trigger(v[n+1],"click"):google.maps.event.trigger(v[0],"click")
			}),
			e(".prevmap-nav").on("click",function(e){
				if(e.preventDefault(),g.setZoom(14),void 0===r) google.maps.event.trigger(v[v.length-1],"click");
				else{
					var n=r;
					n-1<0?google.maps.event.trigger(v[v.length-1],"click"):google.maps.event.trigger(v[n-1],"click")
				}
			});

			var r,g=new google.maps.Map(
				document.getElementById("map-main"),
				{
					zoom:l,
					scrollwheel:s,
					center:mapCenter,
					mapTypeId:google.maps.MapTypeId.ROADMAP,
					zoomControl:!1,
					mapTypeControl:!1,
					scaleControl:!1,
					panControl:!1,
					navigationControl:!1,
					streetViewControl:!1,
					animation:google.maps.Animation.BOUNCE,
					gestureHandling:"cooperative",
					styles:[{featureType:"administrative",elementType:"labels.text.fill",stylers:[{color:"#444444"}]}]
				}
			),
			m=document.createElement("div");

			m.className="map-box";
			var p,c,d={
				content:m,
				disableAutoPan:!0,
				alignBottom:!0,
				maxWidth:300,
				pixelOffset:new google.maps.Size(-140,-45),
				zIndex:null,
				boxStyle:{width:"260px"},
				closeBoxMargin:"0",
				closeBoxURL:"",
				infoBoxClearance:new google.maps.Size(1,1),
				isHidden:!1,
				pane:"floatPane",
				enableEventPropagation:!1
			},
			v=[],u=document.createElement("div");
			for(new function(e,n){
				u.index=1,
				n.controls[google.maps.ControlPosition.RIGHT_CENTER].push(u),
				e.style.padding="5px";
				var o=document.createElement("div");
				e.appendChild(o);
				var a=document.createElement("div");
				a.className="mapzoom-in",o.appendChild(a);
				var t=document.createElement("div");
				t.className="mapzoom-out",
				o.appendChild(t),
				google.maps.event.addDomListener(a,"click",function() {
					n.setZoom(n.getZoom()+1)
				}),
				google.maps.event.addDomListener(t,"click",function(){
					n.setZoom(n.getZoom()-1)
				})
			}(u,g),c=0;c<a.length;c++) {				
				p=new google.maps.Marker({
					animation:google.maps.Animation.DROP,
					position:new google.maps.LatLng(a[c][1],a[c][2]),
					icon:a[c][4],id:c
				}),
				v.push(p);
				var f=new InfoBox;
				google.maps.event.addListener(f,"domready",function(){cardRaining()}),
				google.maps.event.addListener(p,"click",function(n,o){
					return function(){
						f.setOptions(d),m.innerHTML=a[o][0],f.open(g,n),r=n.id;
						var t=new google.maps.LatLng(a[o][1],a[o][2]);
						g.panTo(t),g.panBy(0,-180),
						google.maps.event.addListener(f,"domready",function(){
							e(".infoBox-close").click(function(e){e.preventDefault(),f.close()})
						})
					}
				}(p,c))
		}

		new MarkerClusterer(g,v,{
			imagePath:"images/",
			styles:[{url:"",height:40,width:40}],
			minClusterSize:2
		}),

		google.maps.event.addDomListener(window,"resize",function(){
			var e=g.getCenter();
			google.maps.event.trigger(g,"resize"),g.setCenter(e)
		})
	});


	//Show a single position 

	var map=document.getElementById("singleMap");
	void 0!==map&&null!=map&&google.maps.event.addDomListener(window,"load",function() {
		var cords={
			lng:e("#singleMap").data("longitude"),
			lat:e("#singleMap").data("latitude")
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

		t=(new google.maps.Marker({position:cords,map:map,icon:n,title:"Nuestra ubicación"}),document.createElement("div"));

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