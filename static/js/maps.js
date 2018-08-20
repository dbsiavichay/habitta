document.addEventListener('DOMContentLoaded', function() {
	if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(function(position) {        	
        	buildMap(position.coords.longitude, position.coords.latitude)            
        });
    }else{
    	buildMap(-78.11685009999997, -2.2874005);
    }
});


var buildMap = function (longitude, latitude) {
	var mapCenter = new google.maps.LatLng(latitude,longitude)
	var mapMarker={		
		url:"/static/images/marker.png",		
		anchor:new google.maps.Point(24,50),
	};


	var map=document.getElementById("map-main");
	
	function getMapPopup(e,n,o,a,t,i,l,s){
		return '<div class="map-popup-wrap"><div class="map-popup"><div class="infoBox-close"><i class="fa fa-times"></i></div><div class="map-popup-category">'+n+'</div><a href="'+e+'" class="listing-img-content fl-wrap"><img src="'+o+'" alt=""></a> <div class="listing-content fl-wrap"><div class="card-popup-raining map-card-rainting" data-staRrating="'+l+'"><span class="map-popup-reviews-count">( '+s+' reviews )</span></div><div class="listing-title fl-wrap"><h4><a href='+e+">"+a+'</a></h4><span class="map-popup-location-info"><i class="fa fa-map-marker"></i>'+t+'</span><span class="map-popup-location-phone"><i class="fa fa-phone"></i>'+i+"</span></div></div></div></div>"
	}

	function setData(data) {				
		for(var i in data) {
			var obj = data[i];
			results.push([getMapPopup(obj.url,obj.category,obj.cover,obj.purpose,obj.address,obj.phone,obj.stars,obj.reviews),obj.latitude,obj.longitude,11,mapMarker])					
		}
	}


	var results = [];
	var url = '/api/properties/';
	$.ajax({
		url: url,
		type: 'GET',
		async: false,
		success: setData
	})


	var dataZoom=$("#map-main").attr("data-map-zoom");
	var dataScroll=$("#map-main").attr("data-map-scroll");

	if(void 0!==dataZoom&&false!==dataZoom) var zoom=parseInt(dataZoom);
	else zoom=14;
	if(void 0!==dataScroll&&false!==dataScroll) var scroll=parseInt(dataScroll);
	else scroll=false;
	$(".nextmap-nav").on("click",function(e){
		e.preventDefault(),
		googleMap.setZoom(14);
		var n=r;
		n+1<v.length?google.maps.event.trigger(v[n+1],"click"):google.maps.event.trigger(v[0],"click")
	}),
	$(".prevmap-nav").on("click",function(e){
		if(e.preventDefault(),googleMap.setZoom(14),void 0===r) google.maps.event.trigger(v[v.length-1],"click");
		else{
			var n=r;
			n-1<0?google.maps.event.trigger(v[v.length-1],"click"):google.maps.event.trigger(v[n-1],"click")
		}
	});

	var r;
	var googleMap=new google.maps.Map(
		document.getElementById("map-main"),
		{
			zoom:zoom,
			scrollwheel:scroll,
			center:mapCenter,
			mapTypeId:google.maps.MapTypeId.ROADMAP,
			zoomControl:false,
			mapTypeControl:false,
			scaleControl:false,
			panControl:false,
			navigationControl:false,
			streetViewControl:false,
			animation:google.maps.Animation.BOUNCE,
			gestureHandling:"cooperative",
			styles:[{featureType:"administrative",elementType:"labels.text.fill",stylers:[{color:"#444444"}]}]
		}
	);
	var m=document.createElement("div");
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
	};

	var v=[],u=document.createElement("div");

	for (new function(e,n){		
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
	}(u,googleMap),c=0;c<results.length;c++) {				
		p=new google.maps.Marker({
			animation:google.maps.Animation.DROP,
			position:new google.maps.LatLng(results[c][1],results[c][2]),
			icon:results[c][4],id:c
		}),
		v.push(p);
		var f=new InfoBox;
		google.maps.event.addListener(f,"domready",function(){cardRaining()}),
		google.maps.event.addListener(p,"click",function(n,o){
			return function(){
				f.setOptions(d),m.innerHTML=results[o][0],f.open(googleMap,n),r=n.id;
				var t=new google.maps.LatLng(results[o][1],results[o][2]);
				googleMap.panTo(t),googleMap.panBy(0,-180),
				google.maps.event.addListener(f,"domready",function(){
					$(".infoBox-close").click(function(e){
						e.preventDefault();
						f.close();
					});
				})
			}
		}(p,c))
	}

	new MarkerClusterer(googleMap,v,{
		imagePath:"images/",
		styles:[{url:"",height:40,width:40}],
		minClusterSize:2
	}),

	google.maps.event.addDomListener(window,"resize",function(){
		var e=googleMap.getCenter();
		google.maps.event.trigger(googleMap,"resize"),googleMap.setCenter(e)
	});
}