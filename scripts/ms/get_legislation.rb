require File.join(File.dirname(__FILE__), '..', 'rbutils', 'legislation')

module Mississippi  
  include Scrapable
  
  class Bill
    attr_reader :session
    def initialize(xml, year, session)
      @data = xml
      @year = year
      @session = session
    end
    
    def chamber
      @data.at('measure').inner_text =~ /^h/i ? 'lower' : 'upper'
    end
    
    def bill_id
      @data.at('measure').inner_text
    end
    
    def name
      @data.at('shorttitle').inner_text
    end
    
    def remote_url
      normalize_detail_url(@data.at('actionlink').inner_text)
    end
    
    def primary_sponsor
      detail_page.at('authors/principal/p_name').inner_text.strip
    end
    
    def actions
      hs = detail_page.at('msr_hs').inner_text.strip
      detail_page.search('action').collect do |action|
        text = action.at('act_desc').inner_text.strip
                          #["date", "(s/h/nil)", "s,h,nil", "text"]
        parts = text.scan(/([0-9]{2}\/[0-9]{2})\s*(\((S|H)\)|\s*)(.*)$/i)[0]
        chamber = parts[2].nil? ? '' : parts[2] == 'H' ? 'lower' : 'upper'
        {
          :action_chamber => chamber, 
          :action_text => parts[3], 
          :action_date => Time.parse("#{parts[0]} #{@year}").strftime('%m/%d/%Y')
        }
      end
    end
    
    def versions
      out = []
      types = %w(current intro cmtesub passed asg confrpts amendments vetomsg).join(',')
      detail_page.search(types).each do |v|
        case v.name
          when 'vetomsg'    then url = v.at("veto_other").inner_text.strip
          when 'confrpts'   then url = v.at("cr_other").inner_text.strip
          when 'amendments'
            v.search('amrpt, ham, sam').each do |amd|
              url = amd.at("#{amd.name}_other").inner_text.strip
              out << {:version_name => 'ammendment', :version_url => normalize_version_url(url)}
            end
          else url = v.at("#{v.name}_other").inner_text.strip
        end
        out << {:version_name => v.name, :version_url => normalize_version_url(url)}
      end
      out
    end
    
    def detail_page
      @detail_page ||= Hpricot(open(remote_url))
    end
    
    def to_hash
      {
        :bill_state => 'ms',
        :bill_chamber => chamber,
        :bill_session => @session,
        :bill_id => bill_id,
        :bill_name => name,
        :remote_url => remote_url.to_s
      }
    end
    
    private
      def normalize_detail_url(url)
        path = "#{@year}/pdf/#{url.strip.split('../').last}"
        URI.parse('http://billstatus.ls.state.ms.us') + path
      end
      
      def normalize_version_url(url)
        path = url.strip.split('../').last
        URI.parse('http://billstatus.ls.state.ms.us') + path
      end
  end
  
  def self.state
    "ms"
  end
  
  def self.scrape_bills(chamber, year)
    doc = Hpricot(open("http://billstatus.ls.state.ms.us/#{year}/pdf/all_measures/allmsrs.xml"))
    session = doc.at('formatsession').inner_text
    doc.search('msrgroup').each do |measure|
      bill = Bill.new(measure, year, session)
      if bill.chamber == chamber
        puts "Fetching #{bill.bill_id}"
        
        common_hash = bill.to_hash
        add_bill(common_hash)
        common_hash.delete(:bill_name)
        add_sponsorship(common_hash.merge(
          :sponsor_type => 'primary', 
          :sponsor_name => bill.primary_sponsor
        ))

        bill.actions.each do |action|
          add_action(common_hash.merge(action))
        end
        
        bill.versions.each do |version|
          add_bill_version(common_hash.merge(version))
        end
      end
    end
  end
end

Mississippi.run