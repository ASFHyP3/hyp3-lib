RGB Decomposition
=================

RGB products generated with HyP3 use both co-pol (VV or HH) and cross-pol (VH or HV) backscatter values to generate a color image from SAR data. This approach facilitates visual interpretation by decomposing the signals into surface scattering with some volume scattering (red band), volume scattering (green band), and surface scattering with very low volume scattering (blue band). 

The dual-pol SAR dataset first undergoes radiometric terrain correction (RTC) to adjust for the distortions present in the images due to the side-looking geometry of SAR data acquisition. The RTC images are output in power scale, and any pixels with values less than -48 dB are set to 0. The RGB values are calculated using a combination of the co-pol (CP) and cross-pol (XP) pixel values. The output RGB GeoTIFF is scaled so that the values for each band range from 1 to 255. Zero values are reserved for pixels with no data.

### Interpreting the Images

Calm water generally has very low returns in all polarizations, and areas with very low backscatter will appear blue. Desert landscapes have a backscatter signature similar to that of water, however, so care should be taken in interpretation of the blue color based on the location. 

The green band is determined by the magnitude of the cross-pol returns, which indicates the extent of volume scattering. One of the most common volume scatterers is vegetation, and areas with high cross-pol returns appear more green in the decomposition. There are other volume scatterers, such as glacial ice; areas where the volume to surface scattering ratio is larger than expected for vegetation will display in teal.

The red channel is used to indicate areas that are neither water nor vegetation. Urban areas and other locations with relatively low levels of volume scattering will appear more red in this decomposition.

### Decomposition Calculations

Note that dual-pol image acquisition may provide either VV/VH returns or HH/HV returns, depending on the sensor mode. The same decomposition approach can be applied to either mode; use the co-pol (S<sub>CP</sub>) and cross-pol (S<sub>XP</sub>) pixel values available for the specific dataset. Calculations are applied on a pixel-by-pixel basis.

First, the surface scattering (P<sub>r</sub>) component of the data is calculated as follows:

P<sub>r</sub> = S<sub>CP</sub> - 3 S<sub>XP</sub>

Any negative P<sub>r</sub> values should be set to zero.

A spatial mask is generated using a threshold (*k*) applied to the S<sub>XP</sub> data so that pixels with values below the threshold are included in the blue channel mask (M<sub>B</sub>) and those above the threshold are included in the red band mask (M<sub>R</sub>). Threshold values typically range between -22 and -25 dB, and the default for HyP3 processing is -24 dB. 


M<sub>B</sub> = S<sub>XP</sub> < *k*

M<sub>R</sub> = S<sub>XP</sub> >= *k*

The mask pixels are assigned values of 1 for true and 0 for false. These spatial masks are then applied to the P<sub>r</sub> data to assign the pixels to either the red or the blue band.

P<sub>B</sub> = P<sub>r</sub> M<sub>B</sub>

P<sub>R</sub> = P<sub>r</sub> M<sub>R</sub>

The intensity values for each band are augmented by multiples of the inverse tangent (z):

z = arctan ( (S<sub>CP</sub> -  S<sub>XP</sub>) <sup>0.5</sup> ) 2 / 𝜋

i<sub>R</sub> = 2 (P<sub>R</sub>) <sup>0.5</sup> + z 

i<sub>G</sub> = 3 (S<sub>XP</sub>) <sup>0.5</sup> + 2z

i<sub>B</sub> = 2 (P<sub>B</sub>) <sup>0.5</sup> + 5z

Finally, the values are multiplied by specific scalars to appropriately stretch the dynamic range of each band from 1 to 255. To generate the scaling masks S<sub>R</sub> and S<sub>B</sub>, the masks M<sub>B</sub> and M<sub>R</sub> can be used. Where M = 1, S = 254, and where M = 0, S = 1. For S<sub>G</sub>, the mask can be generated using the i<sub>G</sub> dataset; pixels with values greater than 0 are assigned a value of 254 and zero values are assigned a value of 1.

a<sub>R</sub> = (S<sub>R</sub>) (i<sub>R</sub>) + 1

a<sub>G</sub> = (S<sub>G</sub>) (i<sub>G</sub>) + 1

a<sub>B</sub> = (S<sub>B</sub>) (i<sub>B</sub>) + 1

Any values greater than 255 are set to 255, then the a<sub>RGB</sub> bands are combined to generate an RGB image in 8-bit unsigned integer format.
