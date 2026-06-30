import {useEffect,useRef,useState} from 'react'
import maplibregl, {GeoJSONSource,Map} from 'maplibre-gl'
import type {Asset,Cluster,Earthquake,HotspotPrediction,PopulationExposure} from '../types'

type Props={earthquakes:Earthquake[];clusters:Cluster[];population:PopulationExposure[];assets:Asset[];predictions:HotspotPrediction[];buffer:number;selected:Earthquake|Cluster|HotspotPrediction|null;onSelect:(item:Earthquake|Cluster|HotspotPrediction)=>void;layers:{clusters:boolean,population:boolean,assets:boolean,hotspots:boolean};region:string;theme:'dark'|'light'}
const empty={type:'FeatureCollection',features:[]} as GeoJSON.FeatureCollection
const circle=(lon:number,lat:number,radius:number)=>{const pts=[];for(let i=0;i<=64;i++){const a=i/64*2*Math.PI;pts.push([lon+(radius/111/Math.cos(lat*Math.PI/180))*Math.cos(a),lat+(radius/111)*Math.sin(a)])}return {type:'Polygon',coordinates:[pts]} as GeoJSON.Polygon}
export default function MapView({earthquakes,clusters,population,assets,predictions,buffer,onSelect,layers,region,theme}:Props){
 const node=useRef<HTMLDivElement>(null),map=useRef<Map|null>(null),[ready,setReady]=useState(false)
 const eqRef=useRef(earthquakes),clusterRef=useRef(clusters),hotspotRef=useRef(predictions);eqRef.current=earthquakes;clusterRef.current=clusters;hotspotRef.current=predictions
 useEffect(()=>{if(!node.current)return;const m=new maplibregl.Map({container:node.current,center:[155,0],zoom:1.2,minZoom:1.0,style:{version:8,sources:{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,attribution:'© OpenStreetMap contributors'}},layers:[{id:'osm',type:'raster',source:'osm',paint:{'raster-saturation':-1,'raster-brightness-max':.32,'raster-brightness-min':.02,'raster-contrast':.25}}]}});map.current=m;m.addControl(new maplibregl.NavigationControl({showCompass:false}),'bottom-right');m.on('load',()=>{
  m.addSource('hotspots',{type:'geojson',data:empty});m.addLayer({id:'hotspots-fill',type:'fill',source:'hotspots',paint:{'fill-color':['match',['get','category'],'High','#e3614d','Medium','#dfaa45','#6ca99b'],'fill-opacity':['match',['get','category'],'High',.38,'Medium',.25,.14]}});m.addLayer({id:'hotspots-line',type:'line',source:'hotspots',paint:{'line-color':['match',['get','category'],'High','#f0836d','Medium','#ecc36c','#8cc4b7'],'line-width':['match',['get','category'],'High',1.6,1],'line-opacity':.8}})
  m.addSource('buffers',{type:'geojson',data:empty});m.addLayer({id:'buffers-fill',type:'fill',source:'buffers',paint:{'fill-color':'#c9d968','fill-opacity':.08}});m.addLayer({id:'buffers-line',type:'line',source:'buffers',paint:{'line-color':'#dbea79','line-width':1,'line-dasharray':[3,3],'line-opacity':.65}})
  m.addSource('clusters',{type:'geojson',data:empty});m.addLayer({id:'clusters-fill',type:'fill',source:'clusters',paint:{'fill-color':['match',['get','status'],'Emerging hotspot','#f2b84b','Persistent hotspot','#74d4bc','#7c8292'],'fill-opacity':.16}});m.addLayer({id:'clusters-line',type:'line',source:'clusters',paint:{'line-color':['match',['get','status'],'Emerging hotspot','#f2b84b','Persistent hotspot','#74d4bc','#7c8292'],'line-width':1.5,'line-opacity':.8}})
  m.addSource('earthquakes',{type:'geojson',data:empty});m.addLayer({id:'eq-glow',type:'circle',source:'earthquakes',paint:{'circle-radius':['+',8,['*',['get','magnitude'],2.3]],'circle-color':'#e9ad4b','circle-opacity':.08,'circle-blur':.6}});m.addLayer({id:'earthquakes',type:'circle',source:'earthquakes',paint:{'circle-radius':['+',-2,['*',['get','magnitude'],1.35]],'circle-color':['interpolate',['linear'],['get','magnitude'],4.5,'#f3d779',6,'#efa94c',8,'#ef7452'],'circle-stroke-color':'#fff0ba','circle-stroke-width':.7,'circle-opacity':.94}})
  m.addSource('assets',{type:'geojson',data:empty});m.addLayer({id:'assets',type:'circle',source:'assets',paint:{'circle-radius':4,'circle-color':'#7be0cf','circle-stroke-color':'#09211d','circle-stroke-width':1}})
  setReady(true);m.on('click','hotspots-fill',e=>{const id=e.features?.[0]?.properties?.id;const item=hotspotRef.current.find(x=>x.id===id);if(item)onSelect(item)});m.on('click','earthquakes',e=>{const id=e.features?.[0]?.properties?.id;const item=eqRef.current.find(x=>x.id===id);if(item)onSelect(item)});m.on('click','clusters-fill',e=>{const id=e.features?.[0]?.properties?.id;const item=clusterRef.current.find(x=>x.id===Number(id));if(item)onSelect(item)});['earthquakes','clusters-fill','hotspots-fill'].forEach(id=>{m.on('mouseenter',id,()=>m.getCanvas().style.cursor='pointer');m.on('mouseleave',id,()=>m.getCanvas().style.cursor='')})
 });return()=>m.remove()},[])
 useEffect(()=>{const m=map.current;if(!m?.isStyleLoaded())return;const set=(id:string,data:GeoJSON.FeatureCollection)=>(m.getSource(id) as GeoJSONSource)?.setData(data)
  set('hotspots',{type:'FeatureCollection',features:layers.hotspots?predictions.map(p=>({type:'Feature',properties:{id:p.id,category:p.category,likelihood_score:p.likelihood_score},geometry:p.geometry} as GeoJSON.Feature)):[]})
  set('earthquakes',{type:'FeatureCollection',features:earthquakes.map(e=>({type:'Feature',properties:{...e},geometry:{type:'Point',coordinates:[e.longitude,e.latitude]}}))})
  set('clusters',{type:'FeatureCollection',features:layers.clusters?clusters.map(c=>({type:'Feature',properties:{id:c.id,status:c.status},geometry:c.geometry} as GeoJSON.Feature)):[]})
  const popIds=new Set(population.filter(p=>p[`population_${buffer}km` as keyof PopulationExposure] as number>0).map(p=>p.earthquake_id));set('buffers',{type:'FeatureCollection',features:layers.population?earthquakes.filter(e=>popIds.has(e.id)).map(e=>({type:'Feature',properties:{id:e.id},geometry:circle(e.longitude,e.latitude,buffer)})):[]})
  set('assets',{type:'FeatureCollection',features:layers.assets?assets.filter(a=>a.distance_km<=buffer).map(a=>({type:'Feature',properties:{...a},geometry:{type:'Point',coordinates:[a.longitude,a.latitude]}})):[]})
 },[earthquakes,clusters,population,assets,predictions,buffer,layers,ready])
 useEffect(()=>{const m=map.current;if(!ready||!m?.isStyleLoaded())return;m.setPaintProperty('osm','raster-saturation',theme==='light'?-.55:-1);m.setPaintProperty('osm','raster-brightness-min',theme==='light'?.34:.02);m.setPaintProperty('osm','raster-brightness-max',theme==='light'?.96:.32);m.setPaintProperty('osm','raster-contrast',theme==='light'?-.08:.25)},[theme,ready])
 useEffect(()=>{const active=map.current;if(!ready||!active||!earthquakes.length)return;if(region==='All regions'){active.easeTo({center:[155,0],zoom:1.2,duration:900});return}if(earthquakes.length===1){active.easeTo({center:[earthquakes[0].longitude,earthquakes[0].latitude],zoom:5,duration:900});return}const bounds=new maplibregl.LngLatBounds();earthquakes.forEach(e=>bounds.extend([e.longitude,e.latitude]));active.fitBounds(bounds,{padding:70,maxZoom:5,duration:1000})},[region,ready])
 return <div className="map" ref={node}/>
}







