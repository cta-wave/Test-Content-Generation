import xml.dom.minidom
from wavetcgen.models import TestContent, Mezzanine, CmafStructuralBrand, CmafBrand, PROFILES_TYPE

# Content Model ####################################################################
# Modify the generated content to comply with CTA Content Model
####################################################################################

def title_notice(m:Mezzanine, tc:TestContent):
    media_type, _, _ = PROFILES_TYPE[tc.cmaf_media_profile]
    n = f"{tc.cmaf_media_profile.value}, Test Vector {tc.test_id}"
    if media_type == "video":
        n = f"{m.content.rstrip('_').capitalize()}, {tc.resolution}, {m.fps.to_number()}fps, " + n
    return n


class ContentModel:

    @classmethod
    def patch_mpd(cls, output_file, m:Mezzanine, tc:TestContent):
        cm = ContentModel(output_file, tc.cmaf_structural_brand.value, tc.cmaf_media_profile)
        cm.process(m.copyright_notice, m.source_notice, title_notice(m, tc))
    
    def __init__(self, filename, structural_brand:CmafStructuralBrand, wave_media_profile:CmafBrand):
        self.m_filename = filename
        self.m_structural_brand = structural_brand
        self.m_wave_media_profile = wave_media_profile

    def process(self, copyright_notice, source_notice, title_notice):
        DOMTree = xml.dom.minidom.parse(str(self.m_filename))
        mpd = DOMTree.documentElement
        self.process_mpd(DOMTree, mpd, copyright_notice, source_notice, title_notice)
        with open(self.m_filename, 'w') as f:
            prettyOutput = '\n'.join([line for line in DOMTree.toprettyxml(indent=' '*2).split('\n') if line.strip()])
            f.write(prettyOutput)

    def process_mpd(self, DOMTree, mpd, copyright_notice, source_notice, title_notice):
        profiles = mpd.getAttribute('profiles')
        # TODO: add to the packager command-line
        cta_profile1 = "urn:cta:wave:test-content-media-profile:2022"
        if cta_profile1 not in profiles:
            profiles += "," + cta_profile1
        cta_profile2 = "urn:mpeg:dash:profile:cmaf:2019"
        if cta_profile2 not in profiles:
            profiles += "," + cta_profile2
        mpd.setAttribute('profiles', profiles)
        # ProgramInformation
        program_informations = mpd.getElementsByTagName("ProgramInformation")
        self.remove_element(program_informations)
        program_information = DOMTree.createElement("ProgramInformation")
        title = DOMTree.createElement("Title")
        title_txt = DOMTree.createTextNode(title_notice)
        title.appendChild(title_txt)
        source = DOMTree.createElement("Source")
        source_txt = DOMTree.createTextNode(source_notice)
        source.appendChild(source_txt)
        copyright = DOMTree.createElement("Copyright")
        copyright_txt = DOMTree.createTextNode(copyright_notice)
        copyright.appendChild(copyright_txt)
        program_information.appendChild(title)
        program_information.appendChild(source)
        program_information.appendChild(copyright)
        # Period
        period = mpd.getElementsByTagName("Period").item(0)
        mpd.insertBefore(program_information, period)
        self.process_period(DOMTree, mpd, period)

    def process_period(self, DOMTree, mpd, period):
        # Adaptation Set
        self.process_adaptation_sets(period.getElementsByTagName('AdaptationSet'))

    def process_adaptation_sets(self, adaptation_sets):
        adaptation_set_index = 0
        representation_index = 0
        for adaptation_set in adaptation_sets:
            id = adaptation_set.getAttribute('id')

            content_type = adaptation_set.getAttribute('contentType')
            if  content_type == "":
                representations = adaptation_set.getElementsByTagName('Representation')
                mime_type = representations.item(0).getAttribute('mimeType') if representations.item(0).getAttribute('mimeType') != '' \
                    else adaptation_set.getAttribute('mimeType')
                if 'video' in mime_type:
                    content_type = 'video'
                    adaptation_set.setAttribute('contentType', content_type)
                elif 'audio' in mime_type:
                    content_type = 'audio'
                    adaptation_set.setAttribute('contentType', content_type)
                adaptation_set.setAttribute('containerProfiles', f'{self.m_structural_brand} {self.m_wave_media_profile}')

            representations = adaptation_set.getElementsByTagName('Representation')
            for representation in representations:
                self.process_representation(representation, adaptation_set_index, representation_index, id, content_type)
                representation_index += 1

            adaptation_set_index += 1


    def process_representation(self, representation, adaptation_set_index, representation_index, id, content_type):
        rep_id = content_type + id + "/" + str(representation_index)

    def remove_element(self, nodes):
        for node in nodes:
            parent = node.parentNode
            parent.removeChild(node)
