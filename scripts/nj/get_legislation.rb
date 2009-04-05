# !/usr/bin/ruby
# This module scrapes legislation for New Jersey

module NewJersey
  require File.join(File.dirname(__FILE__), '..', 'rbutils', 'legislation')
  
  include Scrapable
  
  class Bill
    attr_reader :bill_id, :year, :chamber, :actions, :versions, :sponsors, :session
    attr_writer :legislation
    
    def initialize(bill_id, year, chamber)
      @bill_id = bill_id
      @year = year
      @chamber = chamber
      @versions = []
      @sponsors = []
      @actions = []
      @session = "#{year} to #{year.to_i+1} Legislative Session"
    end

    def add_versions(version,link)
      @versions << {:version_name => version,:version_url => "http://www.njleg.state.nj.us#{link}"} 
    end
    
    def add_sponsor(sponsor, type)
      @sponsors << {:sponsor_name => sponsor,:sponsor_type => type}
    end
    
    def add_action(date,action)
      @actions << {:action_chamber=> @chamber, :action_text => action,:action_date => date}
    end
    
    def to_hash
      {
        :bill_state => 'nj',
        :bill_chamber => @chamber,
        :bill_session => @session,
        :bill_id => @bill_id,
        :bill_name => @legislation
      }
    end
  end
  
  
  class NJLegislationSite
    
    attr_reader :record_count, :page_count
    
    def initialize (chamber,year)
      @year = year
      @chamber = chamber
      
      if (bill_db.nil?)
        raise Scrapable::NoDataForYearError.new(year, "Please make sure year is even(i.e., 1996,1998,2000..) and inbetween 1996 and current year")
      end
      
      @base_uri = "http://www.njleg.state.nj.us"
      @agent = WWW::Mechanize.new
      @agent.get(@base_uri)
      @agent.post("#{@base_uri}/bills/bills0001.asp","DBNAME" => bill_db)
      @billpage = fetch_bill_page
      fetch_page_count
    end
    
    
    def fetch_bills_by_page(page)
      result = []
      _billnumbers = bill_numbers(page)
      _billnumbers.each do |bill_id|
        result << fetch_bill(bill_id)
      end
      result
    end
    
    def fetch_bill(bill_id)
      puts "Processing #{bill_id}"
      bill = Bill.new(bill_id,@year,@chamber)
      bdp = Hpricot(fetch_bill_detail_page(bill_id).body) #Fetching Bill Detail Page(bdp) for the bill
      
      #Parsing Legislation
      bdp.search('//td[@bgcolor="#fede7e"]').each do |element|
        element.search('//font[@color="maroon"]').each do |l|
            bill.legislation = (l.inner_html).to_s.strip
        end
      end
      
      #Parsing Sponsors
      sponsor_rows = bdp.search('//table[@width="95%"]').search('//tr')[0].search('//font[@face="Arial, Helvetica, sans-serif"]')
      sponsor_rows.each do |sp|
        sp.inner_html.split(/<br \/>/).each do |spx|
        m =  Hpricot(spx).at("font")
          if !m.nil? 
            sponsor =  m.to_plain_text.split(/\sas\s/)
            #pp m.to_plain_text.split(" as ")
            bill.add_sponsor(sponsor[0].strip,sponsor[1])
          end
        end 
      end
      
      #Parsing actions & versions
      action_rows = bdp.search('//table[@width="95%"]').search('//tr')[3].search('//font')
      actions_version = action_rows[0].inner_html().to_s().split("<br />")
      actions_version.each do |element|
        if(element.include?("<a href"))
          #Parsing Versions - Versions have links, looking up by a href
          version =  element.slice(0..(element.index(/<a href/) - 1)).strip
          link =  Hpricot(element).search('a').last[:href]
          bill.add_versions(version,link)
        elsif (element.include?("<font") || element.empty? )
          # Do Nothing
        else
          #Parsing Actions, seperating datesw
          date = element.strip.slice(0..9).strip
          action = element.gsub(/#{date}/," ").strip
          bill.add_action(date,action)
        end
      end
      bill
    end
    
    private
    
    def bill_db
        case @year
          when 1996; "LIS9697"
          when 1998; "LIS9899"
          when 2000; "LIS2000"
          when 2002; "LIS2002"
          when 2004; "LIS2004"
          when 2006; "LIS2006"
          when 2008; "LIS2008"
          else nil
        end
    end
    
    def get_chamber_from_bill_no(bill_no)
      bill_no.include?("A") ? "lower" : "upper"
    end
    
    def fetch_bill_page(page=1)
      !bill_db.nil? ? @agent.post("#{@base_uri}/bills/BillsByNumber.asp","GoToPage" => page) : nil
    end
    
    def fetch_bill_detail_page(bill_id)
      !bill_db.nil? ? @agent.post("#{@base_uri}/bills/BillView.asp","BillNumber" => bill_id, "LastSession" => "") : nil
     end
     
     def fetch_page_count
       doc = Hpricot(@billpage.body)   
       temp = doc.search("//table[@height='780']//tr//td//table")[1].at("//tr/td/div/font/b/font")
       page_totals = temp.to_plain_text.gsub(/\D/," ").strip.split(" ")
       @record_count = page_totals[0].to_i
       @page_count = page_totals[2].to_i
     end


     def bill_numbers(page=1)
       a_bill_numbers = []
       s_bill_numbers = []
       doc = Hpricot(fetch_bill_page(page).body)
       doc.search("//a[@title='View Detail Bill Information']").each do |bill_element|
         bill_number = (bill_element.inner_html).to_s().slice(/[AS][0-9]{1,10}/)
         get_chamber_from_bill_no(bill_number)=="lower" ? a_bill_numbers << bill_number : s_bill_numbers << bill_number        
       end
       @chamber == "lower" ? a_bill_numbers : s_bill_numbers
     end
  end
 
  def self.state
    "nj"
  end
  
  def self.scrape_bills(chamber, year)
    njs = NJLegislationSite.new(chamber,year.to_i)  
    puts "Total Records found: #{njs.record_count}"
    njs.page_count.times do |page_no|
      puts "Processing Page #{page_no+1} of #{njs.page_count}"
      bills = njs.fetch_bills_by_page(page_no+1)
      bills.each do |bill|
        common_hash = bill.to_hash
        add_bill(common_hash)
        bill.sponsors.each do |sponsor|
          add_sponsorship(common_hash.merge(sponsor))
        end
        bill.versions.each do |version|
          add_bill_version(common_hash.merge(version))
        end
        bill.actions.each do |action|
          add_action(common_hash.merge(action))
        end
      end
    end
  end
  
end

NewJersey.run