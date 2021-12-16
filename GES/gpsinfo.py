"""

(c) 2019 Rechenraum GmbH (office@rechenraum.com)

This file is part of gpsinfo (www.gpsinfo.org).

gpsinfo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

gpsinfo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with gpsinfo. If not, see <http://www.gnu.org/licenses/>.
           

"""

################################################################################
#
# imports
#
################################################################################

import xml.etree.ElementTree as xmlET
import sys
import urllib.request
# sudo apt install python3-gdal
from osgeo import gdal
import math
import numpy
import os

try:
	import qgis.utils
	have_qgis = True
except:
	have_qgis = False

# We support python3 only
assert sys.version_info > (3, 0)

################################################################################
#
# class Service
#
################################################################################

class Service:
	
	#---------------------------------------------------------------------------
		
	# Constructor
	#
	# \param baseurl If given, we connect to the service
	def __init__(self, baseurl = None) :
		self.__isConnected = False
		self.__xmlNamespace = {
			'wmts' : 'http://www.opengis.net/wmts/1.0',
			'ows' : 'http://www.opengis.net/ows/1.1'
		}
		if not baseurl is None : 
			error = self.connect(baseurl)
			if error is str : 
				print(error)
		
	#---------------------------------------------------------------------------
		
	# \brief Checks is a connection could be established successfully
	#
	# This basically means the class was successfully initialized
	#
	# \return True, if connection was successful, false otherwise.
	def isConnected(self):
		return self.__isConnected

	#---------------------------------------------------------------------------

	# \brief Establish connection to a gpsinfo service
	#
	# A successful call to this method is mandatory.
	#
	# \param baseurl Full URL to XML file. For local files, prefix with file://
	#
	# \return String in case of error, nothing in case of success
	def connect(self, baseurl):
		
		self.__isConnected = False
		self.__baseurl = baseurl
		
		# Download XML file
		#	https://stackoverflow.com/a/7244263
		# For local files, use a "file://" prefix, see
		#	https://stackoverflow.com/a/20558624
		try:
			xml = urllib.request.urlopen(baseurl).read().decode('utf-8')		
		except: 
			return "ERROR: Failed to download service XML file from '" + baseurl + "'."
				
		# Parse XML file
		#
		# See https://docs.python.org/3/library/xml.etree.elementtree.html
		#	xmlET.parse(baseurl).getroot()
		# would open a file.
		self.__xmlRoot = xmlET.fromstring(xml)
		
		# Get layers
		self.__layers = []
		for layerNode in self.__xmlRoot.findall('wmts:Contents/wmts:Layer/ows:Title', self.__xmlNamespace):
			self.__layers.append(layerNode.text)
			
		self.__isConnected = True
		
	#---------------------------------------------------------------------------
	
	# \brief Getter for baseurl property
	#
	# \return baseurl of connected service, e.g. URL of XML file
	def baseurl(self):
		if not self.isConnected() : return 'ERROR: You need to successfully connect to a service first.'
		return self.__baseurl
		
	#---------------------------------------------------------------------------
		
	# \brief Get layers of connected service
	#
	# \return String list of layers of connected service
	def layers(self):
		if not self.isConnected() : return 'ERROR: You need to successfully connect to a service first.'
		return self.__layers
		
	#---------------------------------------------------------------------------
			
	# \brief Getter for root of XML element tree of the service's XML file
	#
	# \return Root of XML element tree of the service's XML file
	def xmlRoot(self):
		if not self.isConnected() : return 'ERROR: You need to successfully connect to a service first.'
		return self.__xmlRoot
		
	#---------------------------------------------------------------------------
			
	# \brief Getter for XML namespace
	#
	# \return XML namespace
	def xmlNamespace(self):
		if not self.isConnected() : return 'ERROR: You need to successfully connect to a service first.'
		return self.__xmlNamespace
		
	#---------------------------------------------------------------------------
		
################################################################################
#
# class Layer
#
################################################################################

class Layer:
	
	#---------------------------------------------------------------------------
	
	# Constructor
	#
	# \param service Connect to a layer of this (connected) service
	# \param layerName Name of the layer to connect to
	def __init__(self, service = None, layerName = None ):
		self.__isConnected = False
		self.__nod = None
		if (not service is None) & (not layerName is None) : 
			error = self.connect(service, layerName)
			if error is str : 
				print(error)
		
	#---------------------------------------------------------------------------
		
	# \brief Checks is a connection could be established successfully
	#
	# This basically means the class was successfully initialized
	#
	# \return True, if connection was successful, false otherwise.
	def isConnected(self):
		return self.__isConnected

	#---------------------------------------------------------------------------
		
	# \brief Get no data value
	#
	# The no data value is only available after a successful call to value() or
	# values().
	#
	# \return A string in case of error (e.g. no data value not available) or
	#		the no data value in case of success.
	def nod(self):
		if self.__nod is None :
			return 'ERROR: The no data value is only available after a successful call to value(...) or values(...).'
		return self.__nod

	#---------------------------------------------------------------------------
		
	# \brief Connect to a specific layer
	#
	# \param service Connect to a layer of this (connected) service
	# \param layerName Name of the layer to connect to
	#
	# \return String in case of error
	def connect(self, service, layerName):
		self.__isConnected = False
		if not service.isConnected() : 
			return 'ERROR: You need to pass a successfully connected service.'
			
		layerNode = service.xmlRoot().findall("./wmts:Contents/wmts:Layer[ows:Title='" + layerName + "']", service.xmlNamespace())
		if (len(layerNode) == 0) :
			return 'ERROR: Failed to find layer with title ' + layerName + '.'
		elif (len(layerNode) != 1) :
			return 'ERROR: Failed to find unique layer with title ' + layerName + '.'
		
		self.__layerInfo = { }
		self.__layerInfo['URLFormat'] = layerNode[0].find('wmts:ResourceURL', service.xmlNamespace()).attrib['format']
		self.__layerInfo['URLTemplate'] = layerNode[0].find('wmts:ResourceURL', service.xmlNamespace()).attrib['template']
		
		tileMatrixSet = layerNode[0].find("wmts:TileMatrixSetLink/wmts:TileMatrixSet", service.xmlNamespace()).text
		tileMatrixSetNode = service.xmlRoot().find("./wmts:Contents/wmts:TileMatrixSet[ows:Identifier='" + tileMatrixSet + "']", service.xmlNamespace())
		
		topLeftCorner = tileMatrixSetNode.find('wmts:TileMatrix/wmts:TopLeftCorner', service.xmlNamespace()).text.split()
		self.__layerInfo['topLeftCornerX'] = float(topLeftCorner[0])
		self.__layerInfo['topLeftCornerY'] = float(topLeftCorner[1])
		self.__layerInfo['tileWidth'] = int(tileMatrixSetNode.find('wmts:TileMatrix/wmts:TileWidth', service.xmlNamespace()).text)
		self.__layerInfo['tileHeight'] = int(tileMatrixSetNode.find('wmts:TileMatrix/wmts:TileHeight', service.xmlNamespace()).text)
		self.__layerInfo['nrTilesX'] = int(tileMatrixSetNode.find('wmts:TileMatrix/wmts:MatrixWidth', service.xmlNamespace()).text)
		self.__layerInfo['nrTilesY'] = int(tileMatrixSetNode.find('wmts:TileMatrix/wmts:MatrixHeight', service.xmlNamespace()).text)
		self.__layerInfo['cellsize'] = float(tileMatrixSetNode.find('wmts:TileMatrix/wmts:ScaleDenominator', service.xmlNamespace()).text) * 0.00028
				
		self.__isConnected = True
	
	#---------------------------------------------------------------------------
	
	def __loadTileData(self, tileRowIndex, tileColIndex) :
		# Build URL
		url = self.__layerInfo['URLTemplate'].replace('{TileCol}', str(tileColIndex)).replace('{TileRow}', str(tileRowIndex))
		
		# GDAL's virtual file system: 
		#	https://gdal.org/user/virtual_file_systems.html
		if not url.startswith('file://') : 
			url = '/vsicurl/' + url
		else :
			# We must strip the 'file://' prefix for gdal.Open
			url = url[7:]
		if self.__layerInfo['URLFormat'] == 'application/zip' :
			url = '/vsizip/' + url
		
#		print('Loading ' + url + ' ...')
		
		# GDAL and python: 
		#	- https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html
		#	- https://automating-gis-processes.github.io/2016/Lesson7-read-raster.html
		gdal_dataset = gdal.Open(url)
		if gdal_dataset is None:
			error_string = "ERROR: Failed to open '" + url + "'."
			# There is a bug on windows/qgis/gdal/curl, see 
			#		https://issues.qgis.org/issues/19331
			if (os.system() == 'nt') and have_qgis and (qgis.utils.iface is not None):
				error_string += " gpsinfo failed to access a remote file when running in a Windows qgis/python environment. \
Please check whether the following qgis bug applies in your case: 'http://gpsinfo.org/qgis-opening-remote-files-with-gdal-over-https-fails/#gpsinfo-and-qgis'. \
A quick-and-dirty solution is to call gpsinfo.Layer.allowUnsafeSSL(true)."
				return error_string
			
		# Store latest no data value.
		self.__nod = gdal_dataset.GetRasterBand(1).GetNoDataValue()
					
		# read data as numpy array
		array = gdal_dataset.ReadAsArray()
		
		# Close the dataset
		gdal_dataset = None
		
		return array
	
	#---------------------------------------------------------------------------
	
	# \brief Convert from coordinates to indices
	#
	# (0,0) is top left, x horizontal (column index), y vertical (row index).
	# See also __convertIdx2Coords.
	#
	# \param method 'nearest' (round to nearest), 'upper_left' (floor indices), 
	#		'lower_right' (ceiling indices)
	# \param coordsX Horizontal X coordinate in the layer's CRS of input 
	#		coordinate tuple
	# \param coordsY Vertical Y coordinate in the layer's CRS of input 
	#		coordinate tuple
	#
	# \return In case or error a string. In case of success, a dictionary of
	#		global indices defining the tile and local indices indexing that tile
	def __convertCoords2Idx(self, method, coordsX, coordsY) :
		globalColFloat = (coordsX - self.__layerInfo['topLeftCornerX']) / self.__layerInfo['cellsize']
		globalRowFloat = (self.__layerInfo['topLeftCornerY'] - coordsY) / self.__layerInfo['cellsize']
		
		if method == 'nearest' :
			globalColIndex = int(round(globalColFloat))
			globalRowIndex = int(round(globalRowFloat))
		elif method == 'upper_left' :
			globalColIndex = int(math.floor(globalColFloat))
			globalRowIndex = int(math.floor(globalRowFloat))
		elif method == 'lower_right' :
			globalColIndex = int(math.ceil(globalColFloat))
			globalRowIndex = int(math.ceil(globalRowFloat))
		else :
			return "ERROR: Unknown or unsupported method '" + method + "'."
		
		if (globalColIndex < 0) | (globalRowIndex < 0) :
			return 'ERROR: Query point out of bounds.'
		
		# The wanted value is in tile (tileRowIndex, tileColIndex) at 
		# (localRowIndex, localColIndex)
		tileColIndex, localColIndex = divmod(globalColIndex, self.__layerInfo['tileWidth'])
		tileRowIndex, localRowIndex = divmod(globalRowIndex, self.__layerInfo['tileHeight'])

		if (tileColIndex >= self.__layerInfo['nrTilesX']) | (tileRowIndex >= self.__layerInfo['nrTilesY']) :
			return 'ERROR: Query point out of bounds.'
		
		return { 
			'tileRowIndex' : tileRowIndex, 
			'tileColIndex' : tileColIndex, 
			'localRowIndex' : localRowIndex,
			'localColIndex' : localColIndex
		}

	#---------------------------------------------------------------------------
	
	# \brief Convert from indices to coordinates
	#
	# (0,0) is top left, x horizontal (column index), y vertical (row index).
	# See also __convertCoords2Idx.
	#
	# \param inds Index quadruple dictionary with 'tileRowIndex', 'tileColIndex',
	#		'localRowIndex' and 'localColIndex'
	#
	# \return In case or error a string. In case of success, a coorindate tuple
	#		(x, y)
	def __convertIdx2Coords(self, inds) :
		globalColIndex = inds['tileColIndex']*self.__layerInfo['tileWidth'] + inds['localColIndex']
		globalRowIndex = inds['tileRowIndex']*self.__layerInfo['tileHeight'] + inds['localRowIndex']
		return [
			self.__layerInfo['topLeftCornerX'] + globalColIndex*self.__layerInfo['cellsize'],
			self.__layerInfo['topLeftCornerY'] - globalRowIndex*self.__layerInfo['cellsize']
		]
	
	#---------------------------------------------------------------------------
	
	# \brief Get data at given coordinates
	#
	# \param method See __convertCoords2Idx for documentation. Additionally,
	#		'interpolate' performs bi-linear interpolation.
	# \param x Horizontal X coordinate in the layer's CRS of input 
	#		coordinate tuple
	# \param y Vertical Y coordinate in the layer's CRS of input 
	#		coordinate tuple
	#
	# \return String in case of error, data at the coordinates on success.
	def value(self, method, x, y) :
		if not self.isConnected() : return 'ERROR: You need to successfully connect a layer first.'
		
		if (method == 'interpolate') :
			# Determine indices, beware of tile boundaries
			inds00 = self.__convertCoords2Idx('upper_left', x, y)
			if isinstance(inds00, str) : return inds00
			if not isinstance(inds00, dict) : return 'Error: Unexpected conversion result.'
			inds11 = self.__convertCoords2Idx('lower_right', x, y)
			if isinstance(inds11, str) : return inds11
			if not isinstance(inds11, dict) : return 'Error: Unexpected conversion result.'
			inds01 = { 
				'tileRowIndex' : inds00['tileRowIndex'], 
				'tileColIndex' : inds11['tileColIndex'], 
				'localRowIndex' : inds00['localRowIndex'],
				'localColIndex' : inds11['localColIndex']
			}
			inds10 = { 
				'tileRowIndex' : inds11['tileRowIndex'], 
				'tileColIndex' : inds00['tileColIndex'], 
				'localRowIndex' : inds11['localRowIndex'],
				'localColIndex' : inds00['localColIndex']
			}
			
			# Query data
			data00 = self.__loadTileData(inds00['tileRowIndex'], inds00['tileColIndex'])
			if isinstance(data00, str) : return data00
			v00 = data00[inds00['localRowIndex'],inds00['localColIndex']]
			data01 = self.__loadTileData(inds01['tileRowIndex'], inds01['tileColIndex'])
			if isinstance(data01, str) : return data01
			v01 = data01[inds01['localRowIndex'],inds01['localColIndex']]
			data10 = self.__loadTileData(inds10['tileRowIndex'], inds10['tileColIndex'])
			if isinstance(data10, str) : return data10
			v10 = data10[inds10['localRowIndex'],inds10['localColIndex']]
			data11 = self.__loadTileData(inds11['tileRowIndex'], inds11['tileColIndex'])
			if isinstance(data11, str) : return data11
			v11 = data11[inds11['localRowIndex'],inds11['localColIndex']]
			
			# perform interpolation. ind10 has minimal, ind01 maximal coordinates
			coords10 = self.__convertIdx2Coords(inds10)
			delta_x = (x - coords10[0]) / self.__layerInfo['cellsize']
			delta_y = (y - coords10[1]) / self.__layerInfo['cellsize']
			return (1-delta_y)*((1-delta_x)*v10 + delta_x*v11) + delta_y*((1-delta_x)*v00 + delta_x*v01)			
		else :
			inds = self.__convertCoords2Idx(method, x,y)
			if isinstance(inds, str) : return inds
			if not isinstance(inds, dict) : return 'Error: Unexpected conversion result.'
					
			data = self.__loadTileData(inds['tileRowIndex'], inds['tileColIndex'])
			if isinstance(data, str) : return data
			
			return data[inds['localRowIndex'],inds['localColIndex']]
			
	#---------------------------------------------------------------------------
		
	# \brief Get data of a rectangular coordinate region
	#
	# \param method See __convertCoords2Idx for documentation
	# \param xLowerLeft Horizontal X coordinate in the layer's CRS of the query
	#		rectangles lower left corner
	# \param yLowerLeft Vertical Y coordinate in the layer's CRS of the query
	#		rectangles lower left corner
	# \param xUpperRight Horizontal X coordinate in the layer's CRS of the query
	#		rectangles upper right corner
	# \param yUpperRight Vertical Y coordinate in the layer's CRS of the query
	#		rectangles upper right corner
	#
	# \return String in case of error, numpy data array in case of success
	def values(self, xLowerLeft, yLowerLeft, xUpperRight, yUpperRight):
		if not self.isConnected() : return 'ERROR: You need to successfully connect a layer first.'
		
		if (xLowerLeft > xUpperRight) | (yLowerLeft > yUpperRight) :
			return 'ERROR: Invalid coordinate rectangle.'
		
		# the lower bound indices
		inds0 = self.__convertCoords2Idx('upper_left', xLowerLeft, yUpperRight)
		if isinstance(inds0, str) : return inds0
		# the upper bound indices
		inds1 = self.__convertCoords2Idx('lower_right', xUpperRight, yLowerLeft)
		if isinstance(inds1, str) : return inds1
		
		nrColsTotal = 1 + \
			(inds1['tileColIndex'] * self.__layerInfo['tileWidth'] + inds1['localColIndex']) - \
			(inds0['tileColIndex'] * self.__layerInfo['tileWidth'] + inds0['localColIndex'])
			
		nrRowsTotal = 1 + \
			(inds1['tileRowIndex'] * self.__layerInfo['tileHeight'] + inds1['localRowIndex']) - \
			(inds0['tileRowIndex'] * self.__layerInfo['tileHeight'] + inds0['localRowIndex'])
		
		# print(str((yUpperRight - yLowerLeft) / self.__layerInfo['cellsize']) + ' x ' + str((xUpperRight - xLowerLeft) / self.__layerInfo['cellsize']))
		# print(inds0)
		# print(inds1)
		# print(str(nrRowsTotal) + ' x ' + str(nrColsTotal))
		# print('')
		# print('')
		
		values = numpy.full((nrRowsTotal, nrColsTotal), -1)
		
		for tileRowIndex in range(inds0['tileRowIndex'], inds1['tileRowIndex']+1) :
			# rowValues ... row index of this data block's origin in 'values'
			# rowTileData ... row index of this data block's origin in 'tileData'
			# nrRows ... the data block's number of rows
			if tileRowIndex == inds0['tileRowIndex'] :
				rowValues = 0
				rowTileData = inds0['localRowIndex']
				nrRows = min(self.__layerInfo['tileHeight'] - inds0['localRowIndex'], nrRowsTotal)
			elif tileRowIndex == inds1['tileRowIndex'] :
				rowValues = nrRowsTotal - inds1['localRowIndex'] - 1
				rowTileData = 0
				nrRows = min(inds1['localRowIndex'] + 1, nrRowsTotal)
			else :
				rowValues = (tileRowIndex - inds0['tileRowIndex'] - 1) * self.__layerInfo['tileHeight'] + self.__layerInfo['tileHeight'] - inds0['localRowIndex']
				rowTileData = 0
				nrRows = self.__layerInfo['tileHeight']
			
			for tileColIndex in range(inds0['tileColIndex'], inds1['tileColIndex']+1) :
				# Get tile data
				tileData = self.__loadTileData(tileRowIndex, tileColIndex)
				if isinstance(tileData, str) : return tileData
				
				# colValues ... column index of this data block's origin in 'values'
				# colTileData ... column index of this data block's origin in 'tileData'
				# nrCols ... the data block's number of columns
				if tileColIndex == inds0['tileColIndex'] :
					colValues = 0
					colTileData = inds0['localColIndex']
					nrCols = min(self.__layerInfo['tileWidth'] - inds0['localColIndex'], nrColsTotal)
				elif tileColIndex == inds1['tileColIndex'] :
					colValues = nrColsTotal - inds1['localColIndex'] - 1
					colTileData = 0
					nrCols = min(inds1['localColIndex'] + 1, nrColsTotal)
				else :
					colValues = (tileColIndex - inds0['tileColIndex'] - 1) * self.__layerInfo['tileWidth'] + self.__layerInfo['tileWidth'] - inds0['localColIndex']
					colTileData = 0
					nrCols = self.__layerInfo['tileWidth']
				
				# print(str(rowValues) + ', ' + str(colValues))
				# print(str(rowTileData) + ', ' + str(colTileData))
				# print(str(nrRows) + ', ' + str(nrCols))
				
				# Copy the data
				values[rowValues:rowValues+nrRows,colValues:colValues+nrCols] = \
					tileData[rowTileData:rowTileData+nrRows,colTileData:colTileData+nrCols]

		return values		
        
	#---------------------------------------------------------------------------
			
	# \brief Static method to allow/disallow unsafe SSL, e.g. ignore/respect 
	#		certificate errors.
	#
	# This method is a little helper to resolve problems with qgis on Windows,
	# see 
	#	http://gpsinfo.org/qgis-opening-remote-files-with-gdal-over-https-fails/
	# for more information.
	#
	# \param unsafeSSL If true, we allow unsafe SSL, if false, we disable 
	#		unsafe SSL
	@staticmethod
	def allowUnsafeSSL(unsafeSSL):
		if (unsafeSSL) :
			value='YES'
		else :
			value='NO'
		current_value = gdal.GetConfigOption('GDAL_HTTP_UNSAFESSL')
		if ((current_value is None) or (current_value != value)):
			gdal.SetConfigOption('GDAL_HTTP_UNSAFESSL', value)
			# We clear curl's cache. Curl caches failed requests, and returns
			# errors from the cache.
			gdal.VSICurlClearCache()			

	#---------------------------------------------------------------------------
	
