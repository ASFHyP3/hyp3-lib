RGB Decomposition
=================

RGB products generated with HyP3 use both co-pol (VV or HH) and cross-pol (VH or HV) backscatter values to generate a color image from SAR data. This approach facilitates visual interpretation by decomposing the signals into surface scattering with some volume scattering (red band), volume scattering (green band), and surface scattering with very low volume scattering (blue band). 

The dual-pol SAR dataset first undergoes radiometric terrain correction (RTC) to adjust for the distortions present in the images due to the side-looking geometry of SAR data acquisition. The RTC images are output in amplitude scale, and the RGB values are calculated using a combination of the co-pol (CP) and cross-pol (XP) pixel values. The output RGB GeoTIFF is scaled so that the values for each band range from 1 to 255. Zero values are reserved for pixels with no data.

### Interpreting the Images

Calm water generally has very low returns in all polarizations, and areas with very low backscatter will appear blue. Desert landscapes have a backscatter signature similar to that of water, however, so care should be taken in interpretation of the blue color based on the location. 

The green band is determined by the magnitude of the cross-pol returns, which indicates the extent of volume scattering. One of the most common volume scatterers is vegetation, and areas with high cross-pol returns appear more green in the decomposition. There are other volume scatterers, such as glacial ice, that may also appear as green, so interpretation will be site-dependent.

The red channel is used to indicate areas that are neither water nor vegetation. Urban areas and other locations with relatively low levels of volume scattering will appear more red in this decomposition.

### Decomposition Calculations

Note that dual-pol image acquisition may provide either VV/VH returns or HH/HV returns, depending on the sensor mode. The same decomposition approach can be applied to either mode; use the co-pol (S<sub>CP</sub>) and cross-pol (S<sub>XP</sub>) pixel values available for the specific dataset. 

To calculate the RGB values, the data is first separated into surface (P<sub>r</sub>) and volume (P<sub>v</sub>) scattering components as follows:

P<sub>r</sub> = |S<sub>CP</sub>| <sup>2</sup> - 3 |S<sub>XP</sub>| <sup>2</sup>

P<sub>v</sub> = 4 |S<sub>XP</sub>| <sup>2</sup>

A spatial mask is generated using a threshold (*k*) applied to the P<sub>v</sub> data so that pixels with values below the threshold are included in the blue channel mask (M<sub>B</sub>) and those above the threshold are included in the red band mask (M<sub>R</sub>). Threshold values typically range between -22 and -25 dB, and the default for HyP3 processing is -24 dB.

M<sub>B</sub> = P<sub>v</sub> < *k*

M<sub>R</sub> = P<sub>v</sub> >= *k*

These spatial masks are then applied to the P<sub>r</sub> data to assign the pixels to either the red or the blue band.

P<sub>B</sub> = P<sub>r</sub> M<sub>B</sub>

P<sub>R</sub> = P<sub>r</sub> M<sub>R</sub>

Finally, the intensity values for each band are multiplied by specific scalars to appropriately stretch the dynamic range of each band to create an RGB:

a<sub>R</sub> = 2 (P<sub>R</sub>) <sup>0.5</sup>

a<sub>G</sub> = 3 / 2 (P<sub>v</sub>) <sup>0.5</sup>

a<sub>B</sub> = 5 (P<sub>B</sub>) <sup>0.5</sup>



